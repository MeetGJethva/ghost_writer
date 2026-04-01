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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open Redis + create tables + create consumer group. Shutdown: close/cleanup."""
    # --- startup ---
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_redis()
    await ensure_consumer_group()
    yield
    # --- shutdown ---
    await close_redis()
    await close_db()


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
