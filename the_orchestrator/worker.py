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
# LLM Configuration
# ---------------------------------------------------------------------------

class SelectedProject(BaseModel):
    """Structured response from the LLM routing decision."""
    project_id: str | None = Field(default=None, description="The UUID of the selected project, or None if no project matches.")
    project_name: str | None = Field(default=None, description="The name of the selected project, or None if no project matches.")
    folder_path: str | None = Field(default=None, description="The absolute folder path of the selected project, or None if no project matches.")
    reasoning: str = Field(description="Brief explanation of why this project was selected, or a natural response to the user's query if no project is matched.")


def get_llm():
    """Initialize the Groq LLM with structured output capability."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("[error] GROQ_API_KEY is not set in .env. Please provide a valid key.", file=sys.stderr)
        sys.exit(1)
        
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant", 
        groq_api_key=api_key,
        temperature=0,
    )
    return llm.with_structured_output(SelectedProject)


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


async def process_task(task: Task, projects: List[Project], llm_chain):
    """Use context (projects) and LLM to route the user query."""
    print(f"\n[worker] Processing task {task.task_id} from {task.source_id}")
    print(f"         Query: {task.user_query}")

    if not projects:
        print("         [warning] No projects registered in the database. Cannot route task.")
        return

    # Prepare project context for the prompt
    project_list_str = "\n".join([
        f"- ID: {p.id}\n  Name: {p.name}\n  Folder: {p.folder_path}\n  Keywords: {p.keywords}\n  Description: {p.description}"
        for p in projects
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an intelligent orchestrator. Your job is to match a user query to the most appropriate project "
            "from the list provided. Each project has a name, description, keywords, and folder path.\n\n"
            "PROJECT LIST:\n{projects}\n\n"
            "Give natural response to normal queries and if user query is related to any of the projects, return the project_id.\n"
            "NEVER assume any folder path other than the ones provided in the project list.\n"
            "NEVER assume any project name other than the ones provided in the project list.\n"
            "IF user query is not related to any of the projects, return None as project_id.\n"
        )),
        ("user", "{query}"),
    ])

    try:
        # Run the LLM chain
        chain = prompt | llm_chain
        selection: SelectedProject = await chain.ainvoke({
            "projects": project_list_str,
            "query": task.user_query
        })

        if selection.project_id is None:
            print("         [warning] No project found for the given query.")
            await complete_task(task.task_id, CompleteTaskRequest(
                status=TaskStatus.COMPLETED,
                result=selection.reasoning))
            return

        #===============================  MIMP section ==========================================
        result = understand_codebase(selection.folder_path, task.user_query)
        try:
            related_files = {}
            for file in result["related_files"]:
                related_files[file.path] = file.content

            conversation_history = ""
            conv_id = task.metadata.get("conversation_id")
            source_str = "whatsapp" if getattr(task.source, "value", str(task.source)) == "whatsapp" else None
            
            conversation_history = await fetch_conversation_history(
                conversation_id=conv_id,
                source=source_str,
                source_id=task.source_id
            )

            final_result = acess_code_generator(task.user_query, result["skeleton_path"], result["output_dir"], related_files, conversation_history)
        except Exception as e:
            print(f"         [error] MIMP section failed: {e}")
        #=========================================================================================

        await complete_task(task.task_id, CompleteTaskRequest(
            status=TaskStatus.COMPLETED,
            result= result["summary"] + "\n" + final_result["test_result"])
        )
        # print(result)
    except Exception as e:
        print(f"         [error] LLM routing failed: {e}")


async def worker_main():
    """Main loop: consume from Redis stream and dispatch to LLM router."""
    print("[worker] Starting the-orchestrator worker...")
    
    # Setup dependencies
    await ensure_consumer_group()
    r = await get_redis()
    llm_chain = get_llm()
    
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
                        await process_task(task, projects, llm_chain)

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
