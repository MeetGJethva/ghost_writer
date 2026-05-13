"""
Notifications Ingress — SSE endpoint for pushing real-time Jira alerts.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from the_orchestrator.gateway.redis_client import get_redis

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/sse", summary="Subscribe to real-time Jira notifications")
async def sse_notifications(request: Request):
    """
    Exposes an Server-Sent Events (SSE) stream. Clients will receive
    live notifications published to the 'jira_notifications' Redis channel.
    """
    async def event_generator():
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe("jira_notifications")
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                # Periodically check for new messages
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["data"]:
                    yield f"data: {message['data']}\n\n"
                else:
                    # Keep-alive ping to prevent gateway timeouts
                    yield ": ping\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe("jira_notifications")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
