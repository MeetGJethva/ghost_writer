"""
Worker — background processor that consumes tasks from Redis Streams,
matches them to projects using LLMs (Groq), and identifies the correct folder path.
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import List

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from the_orchestrator.gateway.database import AsyncSessionLocal, engine
from the_orchestrator.gateway.models.db_models import Project, ChatHistory, Conversation
from the_orchestrator.gateway.models.task import Task, TaskStatus
from the_orchestrator.gateway.redis_client import close_redis, get_redis
from the_orchestrator.gateway.stream import CONSUMER_GROUP, STREAM_NAME, ensure_consumer_group
from the_orchestrator.gateway.sources.http_source import complete_task, CompleteTaskRequest
from code_base_understander.main import main as understand_codebase
from code_generator.main import acess_code_generator

load_dotenv()


# ---------------------------------------------------------------------------
# Worker Logic
# ---------------------------------------------------------------------------

async def fetch_projects() -> List[Project]:
    """Retrieve all projects from the database to provide context to the LLM."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project))
        return list(result.scalars().all())


async def fetch_conversation_history(conversation_id: str = None, source: str = None, source_id: str = None) -> str:
    """Retrieve formatted conversation history for context."""
    import uuid
    async with AsyncSessionLocal() as session:
        if source == "whatsapp":
            stmt = select(Conversation).where(Conversation.number == source_id, Conversation.source == "whatsapp")
            result = await session.execute(stmt)
            conv = result.scalars().first()
            if not conv:
                return ""
            conv_id = conv.id
        else:
            if not conversation_id:
                return ""
            try:
                conv_id = uuid.UUID(conversation_id)
            except ValueError:
                return ""
                
        stmt = select(ChatHistory).where(ChatHistory.conversation_id == conv_id).order_by(ChatHistory.created_at)
        result = await session.execute(stmt)
        history = list(result.scalars().all())
        return "\n".join([f"{'Agent' if msg.is_from_agent else 'User'}: {msg.message}" for msg in history])


async def process_task(task: Task, projects: List[Project]):
    """Delegates task processing to the unified Orchestrator Graph."""
    print(f"\n[worker] Processing task {task.task_id} from {task.source_id}")
    print(f"         Query: {task.user_query}")

    # Prepare project context
    projects_data = [
        {
            "id": str(p.id),
            "name": p.name,
            "folder_path": p.folder_path,
            "keywords": p.keywords,
            "description": p.description
        } for p in projects
    ]

    # Fetch conversation history for routing context
    conversation_history = ""
    conv_id = task.metadata.get("conversation_id")
    source_str = "whatsapp" if getattr(task.source, "value", str(task.source)) == "whatsapp" else None
    
    conversation_history = await fetch_conversation_history(
        conversation_id=conv_id,
        source=source_str,
        source_id=task.source_id
    )

    # Check for uploaded files in task metadata
    query_to_send = task.user_query
    file_path = task.metadata.get("file_path")
    file_name = task.metadata.get("file_name", "Uploaded File")
    
    if file_path and os.path.exists(file_path):
        print(f"         [worker] Detected attached file: {file_name} ({file_path})")
        try:
            # Load file data
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Obtain LLM using standard helper
            from code_generator.src.code_generator.config import get_llm, vision_llm
            llm = get_llm()
            vision_llm = vision_llm()
            
            # Run parser gateway
            from the_orchestrator.utils.files_handles.parser_gateway import process_file
            parsed_content = await process_file(
                file_data=file_data,
                file_path=file_path,
                llm=llm,
                vision=vision_llm,
                query=task.user_query
            )
            
            # Append parsed content to user query
            query_to_send = f"{task.user_query}\n\n[Attached Document: {file_name}]\n{parsed_content}"
            print(f"         [worker] Successfully parsed document ({len(parsed_content)} chars)")
        except Exception as e:
            print(f"         [worker] Failed to parse document: {e}")
            query_to_send = f"{task.user_query}\n\n[Attached Document: {file_name} - Processing Failed: {str(e)}]"

    try:
        # Run the unified graph
        final_state = acess_code_generator(
            query=query_to_send,
            projects=projects_data,
            conversation_history=conversation_history
        )

        # Map state back to structured database record
        all_agent_responses = {}
        if final_state.get("understanding_output"):
            all_agent_responses["CodeUnderstandingAgent"] = final_state["understanding_output"]
        if final_state.get("generator_output"):
            all_agent_responses["CodeGeneratorAgent"] = final_state["generator_output"]
        
        status = TaskStatus.COMPLETED if not final_state.get("error") else TaskStatus.FAILED
        
        selected_project = final_state.get("selected_project")
        found_project_id = str(selected_project["id"]) if selected_project else None
        
        await complete_task(task.task_id, CompleteTaskRequest(
            status=status,
            result=final_state.get("final_summary", "Task completed."),
            all_agent_responses=all_agent_responses,
            project_id=found_project_id
        ))

    except Exception as e:
        print(f"         [error] Pipeline execution failed: {e}")
        await complete_task(task.task_id, CompleteTaskRequest(
            status=TaskStatus.FAILED,
            result=f"Processing failed: {str(e)}"
        ))


async def worker_main():
    """Main loop: consume from Redis stream and dispatch to LLM router."""
    print("[worker] Starting the-orchestrator worker...")
    
    # Setup dependencies
    await ensure_consumer_group()
    r = await get_redis()
    
    consumer_name = f"worker-{os.getpid()}"
    print(f"[worker] Consumer name: {consumer_name}")
    print(f"[worker] Listening on stream: {STREAM_NAME}, group: {CONSUMER_GROUP}")

    try:
        while True:
            # Block for up to 5 seconds waiting for new messages
            # Use XREADGROUP to handle multiple workers and reliable delivery
            try:
                response = await r.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=consumer_name,
                    streams={STREAM_NAME: ">"},
                    count=1,
                    block=5000,
                )
            except Exception as e:
                print(f"[worker] Error reading from stream: {e}")
                await asyncio.sleep(1)
                continue

            if not response:
                continue

            # response format: [[stream_name, [[entry_id, payload_dict]], ...]]
            for stream, messages in response:
                for entry_id, payload in messages:
                    try:
                        task = Task.from_stream_payload(payload)
                        projects = await fetch_projects()
                        await process_task(task, projects)

                        # Acknowledge the message so it's not redelivered
                        await r.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                        # Optionally delete from stream if we don't need history
                        # await r.xdel(STREAM_NAME, entry_id)
                        
                    except Exception as e:
                        print(f"[worker] Failed to process message {entry_id}: {e}")

    except asyncio.CancelledError:
        print("[worker] Stopping...")
    finally:
        await close_redis()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(worker_main())
    except KeyboardInterrupt:
        print("[worker] Interrupted by user")
