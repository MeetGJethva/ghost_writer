"""
Task Tracker — persists task state in Redis Hashes so responses can
always be routed back to the original caller, even across restarts.

Key schema:  tasks:registry:<task_id>   (Hash)
TTL:         24 hours
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from the_orchestrator.gateway.models.task import Task, TaskStatus
from the_orchestrator.gateway.redis_client import get_redis

_TASK_TTL_SECONDS = 60 * 60 * 24  # 24 h


def _registry_key(task_id: str) -> str:
    return f"tasks:registry:{task_id}"


async def register_task(task: Task) -> None:
    """Store initial task state when it first arrives at the gateway."""
    r = await get_redis()
    key = _registry_key(task.task_id)
    await r.hset(key, mapping=task.to_stream_payload())
    await r.expire(key, _TASK_TTL_SECONDS)


async def update_task(
    task_id: str,
    status: TaskStatus,
    result: str | None = None,
    completion_time: datetime | None = None,
) -> None:
    """
    Update status (and optionally result + completion_time) for a tracked task.
    Called by the worker when it finishes processing.
    """
    r = await get_redis()
    key = _registry_key(task_id)
    updates: dict[str, str] = {"status": status.value}
    if result is not None:
        updates["result"] = result
    if completion_time is not None:
        updates["completion_time"] = completion_time.isoformat()
    else:
        updates["completion_time"] = datetime.now(timezone.utc).isoformat()
    await r.hset(key, mapping=updates)
    # Refresh TTL on every update so active tasks don't expire mid-processing
    await r.expire(key, _TASK_TTL_SECONDS)


async def get_task(task_id: str) -> Task | None:
    """Fetch the current state of a task from the registry. Returns None if not found."""
    r = await get_redis()
    key = _registry_key(task_id)
    payload = await r.hgetall(key)
    if not payload:
        return None
    return Task.from_stream_payload(payload)
