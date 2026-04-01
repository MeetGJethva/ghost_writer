"""
CLI Source — submit and poll tasks directly from the terminal.

Usage:
    uv run python -m gateway.sources.cli_source submit --query "..." --source-id "me"
    uv run python -m gateway.sources.cli_source status --task-id "<uuid>"
"""
from __future__ import annotations

import asyncio
import json
import sys

import click

from gateway.models.task import SourceType, Task
from gateway.redis_client import close_redis
from gateway.stream import publish_task
from gateway.tracker import get_task, register_task


def _run(coro):
    """Helper to run an async coroutine from a sync Click command."""
    return asyncio.run(coro)


@click.group()
def cli():
    """The-Orchestrator gateway CLI."""
    pass


@cli.command("submit")
@click.option("--query", "-q", required=True, help="The user query to process.")
@click.option(
    "--source-id",
    "-s",
    default="cli-user",
    show_default=True,
    help="Identifier for the caller (username, machine name, etc.).",
)
@click.option(
    "--metadata",
    "-m",
    default="{}",
    show_default=True,
    help="Optional JSON string with extra metadata to attach to the task.",
)
def submit(query: str, source_id: str, metadata: str):
    """Submit a new task to the Redis Stream."""

    async def _submit():
        try:
            extra = json.loads(metadata)
        except json.JSONDecodeError:
            click.echo(f"[error] --metadata must be valid JSON. Got: {metadata}", err=True)
            sys.exit(1)

        task = Task(
            source=SourceType.CLI,
            source_id=source_id,
            user_query=query,
            metadata=extra,
        )

        await register_task(task)
        entry_id = await publish_task(task)
        await close_redis()

        click.echo(
            json.dumps(
                {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "arrival_time": task.arrival_time.isoformat(),
                    "stream_entry_id": entry_id,
                },
                indent=2,
            )
        )

    _run(_submit())


@cli.command("status")
@click.option("--task-id", "-t", required=True, help="UUID of the task to check.")
def check_status(task_id: str):
    """Fetch the current status of a task."""

    async def _status():
        task = await get_task(task_id)
        await close_redis()

        if task is None:
            click.echo(f"[error] Task '{task_id}' not found.", err=True)
            sys.exit(1)

        click.echo(
            json.dumps(
                {
                    "task_id": task.task_id,
                    "source": task.source.value,
                    "source_id": task.source_id,
                    "user_query": task.user_query,
                    "status": task.status.value,
                    "arrival_time": task.arrival_time.isoformat(),
                    "completion_time": (
                        task.completion_time.isoformat() if task.completion_time else None
                    ),
                    "result": task.result,
                    "metadata": task.metadata,
                },
                indent=2,
            )
        )

    _run(_status())


if __name__ == "__main__":
    cli()
