"""
Task model — core data object that flows through the gateway and Redis Streams.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Identifies where a task originated from."""
    HTTP = "HTTP"
    WHATSAPP = "WHATSAPP"
    CLI = "CLI"
    JIRA = "JIRA"


class TaskStatus(str, Enum):
    """Lifecycle of a task as it moves through the system."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(BaseModel):
    """
    The canonical task object that is created at ingress, published to
    Redis Streams, and updated when the worker completes the work.
    """
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier (UUIDv4)",
    )
    source: SourceType = Field(
        description="Which ingress channel created this task",
    )
    source_id: str = Field(
        description=(
            "Caller identifier: phone number (WhatsApp), IP/user-agent (HTTP), "
            "username (CLI), etc."
        ),
    )
    user_query: str = Field(
        description="The raw text query or message submitted by the user",
    )
    arrival_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the task entered the gateway",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current lifecycle status of the task",
    )
    completion_time: datetime | None = Field(
        default=None,
        description="UTC timestamp when the task was completed or failed",
    )
    result: str | None = Field(
        default=None,
        description="Response payload produced by the worker",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra data attached by the ingress source",
    )

    def to_stream_payload(self) -> dict[str, str]:
        """Serialize to a flat dict suitable for Redis XADD (all values must be str)."""
        return {
            "task_id": self.task_id,
            "source": self.source.value,
            "source_id": self.source_id,
            "user_query": self.user_query,
            "arrival_time": self.arrival_time.isoformat(),
            "status": self.status.value,
            "completion_time": self.completion_time.isoformat() if self.completion_time else "",
            "result": self.result or "",
            "metadata": str(self.metadata),
        }

    @classmethod
    def from_stream_payload(cls, payload: dict[str, str]) -> "Task":
        """Reconstruct a Task from a Redis stream message dict."""
        import ast
        return cls(
            task_id=payload["task_id"],
            source=SourceType(payload["source"]),
            source_id=payload["source_id"],
            user_query=payload["user_query"],
            arrival_time=datetime.fromisoformat(payload["arrival_time"]),
            status=TaskStatus(payload["status"]),
            completion_time=(
                datetime.fromisoformat(payload["completion_time"])
                if payload.get("completion_time")
                else None
            ),
            result=payload.get("result") or None,
            metadata=ast.literal_eval(payload.get("metadata", "{}")) or {},
        )
