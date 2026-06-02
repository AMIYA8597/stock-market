"""
WebSocket connection manager for real-time market data streaming.

Manages active WebSocket connections per channel (symbol, portfolio, alerts).
Supports broadcasting to all subscribers of a given channel.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """
    Manages WebSocket connections grouped by channel.

    Channels follow the pattern: "market:{symbol}", "portfolio:{user_id}", "alerts:{user_id}"
    """

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept a WebSocket connection and add it to the specified channel."""
        await websocket.accept()
        async with self._lock:
            self._channels[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Remove a WebSocket connection from the specified channel."""
        async with self._lock:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
        logger.info(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, channel: str, data: Any) -> None:
        """
        Broadcast a JSON message to all connections on a channel.

        Automatically removes dead connections.
        """
        message = json.dumps(data) if not isinstance(data, str) else data
        dead: list[WebSocket] = []

        async with self._lock:
            connections = list(self._channels.get(channel, set()))

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._channels[channel].discard(ws)

    async def send_personal(self, websocket: WebSocket, data: Any) -> None:
        """Send a JSON message to a specific WebSocket connection."""
        message = json.dumps(data) if not isinstance(data, str) else data
        await websocket.send_text(message)

    @property
    def active_channels(self) -> list[str]:
        """Return list of channels with active connections."""
        return list(self._channels.keys())

    def channel_count(self, channel: str) -> int:
        """Return the number of active connections on a channel."""
        return len(self._channels.get(channel, set()))


# Singleton instance used across the application
ws_manager = ConnectionManager()
