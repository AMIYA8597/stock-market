"""
WebSocket connection manager for real-time market data streaming.

Manages active WebSocket connections per channel (symbol, portfolio, alerts).
Supports broadcasting to all subscribers of a given channel.
Implements subscribe/unsubscribe, ping/pong heartbeats, and clean teardown.
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
        # Maps channel name -> set of WebSockets
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # Maps WebSocket -> set of channel names it is subscribed to
        self._subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        # Maps WebSocket -> background heartbeat task
        self._heartbeats: dict[WebSocket, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and start its heartbeat."""
        await websocket.accept()
        logger.info("WebSocket connected")

        # Start heartbeat loop for this connection
        task = asyncio.create_task(self._heartbeat_loop(websocket))
        async with self._lock:
            self._heartbeats[websocket] = task

    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        """Periodic ping to ensure connection is alive."""
        try:
            while True:
                await asyncio.sleep(30)  # 30s heartbeat interval
                try:
                    await self.send_personal(
                        websocket,
                        {
                            "type": "heartbeat",
                            "symbol": None,
                            "payload": {"ping": True},
                            "ts": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
                            "source": "system"
                        }
                    )
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect(websocket)

    async def subscribe(self, websocket: WebSocket, channel: str) -> None:
        """Subscribe a WebSocket to a specific channel."""
        async with self._lock:
            self._channels[channel].add(websocket)
            self._subscriptions[websocket].add(channel)
        logger.debug(f"WebSocket subscribed to channel: {channel}")

    async def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        """Unsubscribe a WebSocket from a specific channel."""
        async with self._lock:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
            self._subscriptions[websocket].discard(channel)
        logger.debug(f"WebSocket unsubscribed from channel: {channel}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Clean teardown: remove from all channels, cancel heartbeat."""
        async with self._lock:
            # Cancel heartbeat task
            if websocket in self._heartbeats:
                self._heartbeats[websocket].cancel()
                del self._heartbeats[websocket]

            # Remove from all subscribed channels
            for channel in list(self._subscriptions.get(websocket, set())):
                self._channels[channel].discard(websocket)
                if not self._channels[channel]:
                    del self._channels[channel]

            if websocket in self._subscriptions:
                del self._subscriptions[websocket]

        logger.info("WebSocket disconnected cleanly")

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
            for ws in dead:
                await self.disconnect(ws)

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
