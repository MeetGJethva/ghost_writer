"""
Redis Streams — publish tasks and manage consumer group setup.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

from the_orchestrator.gateway.models.task import Task
from the_orchestrator.gateway.redis_client import get_redis

load_dotenv()

STREAM_NAME: str = os.getenv("STREAM_NAME", "tasks:incoming")
STREAM_MAX_LEN: int = int(os.getenv("STREAM_MAX_LEN", "10000"))
CONSUMER_GROUP: str = os.getenv("CONSUMER_GROUP", "orchestrator-workers")


async def ensure_consumer_group() -> None:
    """
    Create the consumer group on the stream if it doesn't exist yet.
    Called once at application startup.
    """
    r = await get_redis()
    try:
        await r.xgroup_create(
            name=STREAM_NAME,
            groupname=CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
    except Exception as exc:
        # BUSYGROUP means the group already exists — that's fine
        if "BUSYGROUP" not in str(exc):
            raise


async def publish_task(task: Task) -> str:
    """
    Publish a task to the Redis Stream.

    Returns the stream entry ID assigned by Redis.
    """
    r = await get_redis()
    payload = task.to_stream_payload()
    entry_id: str = await r.xadd(
        name=STREAM_NAME,
        fields=payload,
        maxlen=STREAM_MAX_LEN,
        approximate=True,
    )
    return entry_id
