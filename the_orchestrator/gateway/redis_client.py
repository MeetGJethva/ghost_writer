"""
Redis async client — single shared connection pool for the gateway.
"""
from __future__ import annotations

import os

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

_redis_client: aioredis.Redis | None = None


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379")


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            get_redis_url(),
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Gracefully close the Redis connection (call on app shutdown)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
