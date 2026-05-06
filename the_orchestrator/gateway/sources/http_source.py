"""
HTTP Source — FastAPI router for generic HTTP task submission.

Any client (browser, curl, WhatsApp client, mobile app, etc.) can
POST to /api/tasks to submit a task.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import uuid

from the_orchestrator.gateway.database import get_db
from the_orchestrator.gateway.models.db_models import Conversation, ChatHistory, FileChange
from the_orchestrator.gateway.ws_manager import manager as ws_manager

from the_orchestrator.gateway.models.task import SourceType, Task, TaskStatus
from the_orchestrator.gateway.stream import publish_task
from the_orchestrator.gateway.tracker import get_task, register_task, update_task

router = APIRouter(prefix="/api", tags=["tasks"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SubmitTaskRequest(BaseModel):
    query: str = Field(..., description="The user query or message to process")
    source_id: str = Field(
        ...,
        description=(
            "Caller identifier: e.g. phone number, user ID, IP address, "
            "or any string that uniquely identifies the requester"
        ),
    )
    source: SourceType = Field(
        default=SourceType.HTTP,
        description="Originating source type (defaults to HTTP)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra context to attach to the task",
    )
    conversation_id: str | None = Field(
        None,
        description="Optional conversation ID for extending an existing thread. Used if not from whatsapp.",
    )
    project_id: str | None = Field(
        None,
        description="Optional project ID to associate with the task and chat history.",
    )


class SubmitTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    arrival_time: datetime
    stream_entry_id: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    source: SourceType
    source_id: str
    user_query: str
    status: TaskStatus
    arrival_time: datetime
    completion_time: datetime | None
    result: str | None
    metadata: dict[str, Any]

class FileChangeResponse(BaseModel):
    file_name: str
    hash: str

class ChatHistoryMessageResponse(BaseModel):
    id: str
    is_from_agent: bool
    source: str
    message: str
    all_agent_responses: dict[str, Any] | None = None
    timestamp: str  
    file_changes: list[FileChangeResponse] = []
    project_id: str | None = None

class ConversationResponse(BaseModel):
    id: str
    source: str
    number: str | None


class CompleteTaskRequest(BaseModel):
    status: TaskStatus = Field(..., description="Final status: COMPLETED or FAILED")
    result: str | None = Field(None, description="Response payload from the worker (summary)")
    all_agent_responses: dict[str, Any] | None = Field(None, description="Verbatim responses from each agent")
    completion_time: datetime | None = Field(
        None,
        description="When the task finished (defaults to now if omitted)",
    )
    project_id: str | None = Field(
        None,
        description="Project ID determined by the worker",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/tasks",
    response_model=SubmitTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new task",
    description=(
        "Creates a Task, registers it in the tracker, and publishes it to "
        "the Redis Stream for worker consumption."
    ),
)
async def submit_task(
    body: SubmitTaskRequest,
    db: AsyncSession = Depends(get_db)
) -> SubmitTaskResponse:
    conversation = None
    
    if body.source == SourceType.WHATSAPP:
        stmt = select(Conversation).where(
            Conversation.number == body.source_id,
            Conversation.source == "whatsapp"
        )
        result = await db.execute(stmt)
        conversation = result.scalars().first()
        
        if not conversation:
            conversation = Conversation(source="whatsapp", number=body.source_id)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
    else:
        if body.conversation_id:
            try:
                conv_uuid = uuid.UUID(body.conversation_id)
                stmt = select(Conversation).where(Conversation.id == conv_uuid)
                result = await db.execute(stmt)
                conversation = result.scalars().first()
            except ValueError:
                pass
                
        if not conversation:
            conversation = Conversation(source=body.source.value)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

    # Create entry in chat history
    proj_uuid = None
    if body.project_id:
        try:
            proj_uuid = uuid.UUID(body.project_id)
        except ValueError:
            pass

    chat_entry = ChatHistory(
        conversation_id=conversation.id,
        message=body.query,
        is_from_agent=False,
        project_id=proj_uuid
    )
    db.add(chat_entry)
    await db.commit()
    await db.refresh(chat_entry)

    # Broadcast user message to connected WebSocket clients
    await ws_manager.broadcast(str(conversation.id), {
        "type": "new_message",
        "message": {
            "id": str(chat_entry.id),
            "is_from_agent": False,
            "source": conversation.source,
            "message": body.query,
            "timestamp": chat_entry.created_at.strftime("%I:%M %p"),
            "file_changes": [],
            "project_id": str(chat_entry.project_id) if chat_entry.project_id else None
        }
    })

    # Ensure task metadata knows about the DB records so workers can reference them
    body.metadata["conversation_id"] = str(conversation.id)
    body.metadata["chat_history_id"] = str(chat_entry.id)
    if proj_uuid:
        body.metadata["project_id"] = str(proj_uuid)

    task = Task(
        source=body.source,
        source_id=body.source_id,
        user_query=body.query,
        metadata=body.metadata,
    )

    # Persist to registry first so workers can write back results
    await register_task(task)

    # Publish to Redis Stream
    entry_id = await publish_task(task)

    return SubmitTaskResponse(
        task_id=task.task_id,
        status=task.status,
        arrival_time=task.arrival_time,
        stream_entry_id=entry_id,
        message="Task accepted and queued for processing.",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get task status",
    description="Poll the current state of a task by its ID.",
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    task = await get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )
    return TaskStatusResponse(
        task_id=task.task_id,
        source=task.source,
        source_id=task.source_id,
        user_query=task.user_query,
        status=task.status,
        arrival_time=task.arrival_time,
        completion_time=task.completion_time,
        result=task.result,
        metadata=task.metadata,
    )


@router.patch(
    "/tasks/{task_id}/complete",
    response_model=TaskStatusResponse,
    summary="Mark task as completed or failed",
    description=(
        "Called by a worker (or any internal service) to update the task "
        "status and attach the result payload. This allows the original "
        "caller to retrieve the response via GET /api/tasks/{task_id}."
    ),
)
async def complete_task(task_id: str, body: CompleteTaskRequest) -> TaskStatusResponse:
    task = await get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    completion_time = body.completion_time or datetime.now(timezone.utc)
    await update_task(
        task_id=task_id,
        status=body.status,
        result=body.result,
        completion_time=completion_time,
        notify=True,
    )

    if task.metadata.get("conversation_id"):
        from the_orchestrator.gateway.database import AsyncSessionLocal
        import uuid as _uuid
        async with AsyncSessionLocal() as session:
            try:
                conv_id = _uuid.UUID(task.metadata["conversation_id"])
                proj_id_str = body.project_id or task.metadata.get("project_id")
                
                # Update user message project_id if not set
                if proj_id_str and task.metadata.get("chat_history_id"):
                    user_msg_stmt = select(ChatHistory).where(ChatHistory.id == _uuid.UUID(task.metadata["chat_history_id"]))
                    user_msg_result = await session.execute(user_msg_stmt)
                    user_msg = user_msg_result.scalars().first()
                    if user_msg and not user_msg.project_id:
                        user_msg.project_id = _uuid.UUID(proj_id_str)

                agent_msg = ChatHistory(
                    conversation_id=conv_id,
                    message=body.result or "Task completed.",
                    all_agent_responses=body.all_agent_responses,
                    is_from_agent=True,
                    project_id=_uuid.UUID(proj_id_str) if proj_id_str else None
                )
                session.add(agent_msg)
                await session.commit()
                await session.refresh(agent_msg)

                # Broadcast agent response over WebSocket
                await ws_manager.broadcast(str(conv_id), {
                    "type": "new_message",
                        "message": {
                            "id": str(agent_msg.id),
                            "is_from_agent": True,
                            "source": "web",
                            "message": agent_msg.message,
                            "all_agent_responses": agent_msg.all_agent_responses,
                            "timestamp": agent_msg.created_at.strftime("%I:%M %p"),
                            "file_changes": [],
                            "project_id": str(agent_msg.project_id) if agent_msg.project_id else None
                        }
                })
            except Exception as e:
                print(f"Failed to insert agent chat history: {e}")

    # Return the latest state
    updated_task = await get_task(task_id)
    return TaskStatusResponse(
        task_id=updated_task.task_id,
        source=updated_task.source,
        source_id=updated_task.source_id,
        user_query=updated_task.user_query,
        status=updated_task.status,
        arrival_time=updated_task.arrival_time,
        completion_time=updated_task.completion_time,
        result=updated_task.result,
        metadata=updated_task.metadata,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="Get all conversations"
)
async def get_conversations(db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    return [
        ConversationResponse(
            id=str(c.id),
            source=c.source,
            number=c.number
        ) for c in conversations
    ]

@router.get(
    "/conversations/{conversation_id}/history",
    response_model=list[ChatHistoryMessageResponse],
    summary="Get chat history for a conversation"
)
async def get_conversation_history(conversation_id: str, db: AsyncSession = Depends(get_db)):
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    stmt = (
        select(ChatHistory)
        .where(ChatHistory.conversation_id == conv_uuid)
        .options(selectinload(ChatHistory.file_changes), selectinload(ChatHistory.conversation))
        .order_by(ChatHistory.created_at.asc())
    )
    result = await db.execute(stmt)
    history = result.scalars().all()

    response = []
    for msg in history:
        file_changes = [
            FileChangeResponse(file_name=fc.file_name, hash=fc.hash) 
            for fc in msg.file_changes
        ]
        response.append(ChatHistoryMessageResponse(
            id=str(msg.id),
            is_from_agent=msg.is_from_agent,
            source="whatsapp" if msg.conversation.source == "whatsapp" else "web",
            message=msg.message,
            all_agent_responses=msg.all_agent_responses,
            timestamp=msg.created_at.strftime("%I:%M %p"),
            file_changes=file_changes,
            project_id=str(msg.project_id) if msg.project_id else None
        ))
    return response


class SuccessResponse(BaseModel):
    success: bool
    message: str | None = None


@router.delete(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse,
    summary="Delete a conversation and all its history"
)
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    stmt = select(Conversation).where(Conversation.id == conv_uuid)
    result = await db.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return SuccessResponse(success=True, message="Conversation deleted successfully")
