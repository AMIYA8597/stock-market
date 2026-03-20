"""Redis-backed signal broadcaster for WebSocket clients."""

from __future__ import annotations

import json

from redis.asyncio import Redis

from app.websocket.connection_manager import get_connection_manager


async def run_signal_broadcaster(redis_client: Redis) -> None:
    """Consume signal updates from Redis and broadcast to websocket channel."""
    manager = get_connection_manager()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("signals.updates")

    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload_raw = message.get("data")
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            await manager.broadcast("signals:global", payload)
    finally:
        await pubsub.unsubscribe("signals.updates")
        await pubsub.close()
