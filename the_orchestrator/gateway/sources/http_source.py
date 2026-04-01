"""
HTTP Source — FastAPI router for generic HTTP task submission.

Any client (browser, curl, WhatsApp client, mobile app, etc.) can
POST to /api/tasks to submit a task.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

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


class CompleteTaskRequest(BaseModel):
    status: TaskStatus = Field(..., description="Final status: COMPLETED or FAILED")
    result: str | None = Field(None, description="Response payload from the worker")
    completion_time: datetime | None = Field(
        None,
        description="When the task finished (defaults to now if omitted)",
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
async def submit_task(body: SubmitTaskRequest) -> SubmitTaskResponse:
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
    )

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
