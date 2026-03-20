"""Application startup and shutdown event handlers."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from loguru import logger

from app.database.redis_client import get_redis
from app.websocket.price_broadcaster import run_price_broadcaster
from app.websocket.signal_broadcaster import run_signal_broadcaster


async def startup_events() -> list[asyncio.Task]:
    """Start background websocket broadcasters and warm integrations."""
    redis_client = get_redis()

    tasks = [
        asyncio.create_task(run_price_broadcaster(redis_client), name="price_broadcaster"),
        asyncio.create_task(run_signal_broadcaster(redis_client), name="signal_broadcaster"),
    ]
    logger.info("Startup complete: websocket broadcasters launched")
    return tasks


async def shutdown_events(tasks: list[asyncio.Task]) -> None:
    """Gracefully cancel background tasks."""
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
    logger.info("Shutdown complete: background tasks cancelled")
