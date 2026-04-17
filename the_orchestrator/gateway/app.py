"""
FastAPI application factory — wires together all ingress routers,
Redis lifecycle hooks, and health check.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from the_orchestrator.gateway.database import Base, close_db, engine, get_db
from the_orchestrator.gateway.redis_client import close_redis, get_redis
from the_orchestrator.gateway.sources.http_source import router as http_router
from the_orchestrator.gateway.project_register import router as project_router
from the_orchestrator.gateway.stream import ensure_consumer_group


import asyncio
from the_orchestrator.gateway.ws_manager import manager as ws_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open Redis + create tables + create consumer group. Shutdown: close/cleanup."""
    # --- startup ---
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_redis()
    await ensure_consumer_group()
    
    # Start Redis Pub/Sub listener for WebSockets
    ws_task = asyncio.create_task(ws_manager.start_redis_listener())
    
    yield
    # --- shutdown ---
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass
        
    await close_redis()
    await close_db()


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="The Orchestrator — API Gateway",
    description=(
        "Multi-source API gateway that accepts tasks from HTTP, WhatsApp clients, "
        "and CLI tools. Each task is normalized, registered in a Redis tracker, "
        "and published to a Redis Stream for worker consumption."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(http_router)
app.include_router(project_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"], summary="Health check")
async def health() -> JSONResponse:
    """Returns 200 OK when the gateway and Redis connection are healthy."""
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return JSONResponse(
        status_code=200 if redis_ok else 503,
        content={"status": "ok" if redis_ok else "degraded", "redis": redis_ok},
    )


# ---------------------------------------------------------------------------
# WebSocket — real-time chat updates
# ---------------------------------------------------------------------------
from fastapi import WebSocket, WebSocketDisconnect
from the_orchestrator.gateway.ws_manager import manager as ws_manager

@app.websocket("/ws/conversations/{conversation_id}")
async def websocket_conversation(websocket: WebSocket, conversation_id: str):
    """Stream new messages for a conversation in real-time."""
    print("conversation_id", conversation_id)
    await ws_manager.connect(conversation_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings or we just wait
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(conversation_id, websocket)
