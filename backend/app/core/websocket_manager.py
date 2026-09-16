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
        # Maps IP -> count of active connections
        self._ip_counts: dict[str, int] = defaultdict(int)
        # A single browser can legitimately open several sockets from one IP
        # (prices, signals, alerts, plus multiple tabs) — this caps abuse, not
        # normal multi-tab usage.
        self.MAX_CONNECTIONS_PER_IP = 30
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and start its heartbeat."""
        from fastapi import WebSocketException

        client_ip = websocket.client.host if websocket.client else "unknown"

        async with self._lock:
            if client_ip != "unknown" and self._ip_counts[client_ip] >= self.MAX_CONNECTIONS_PER_IP:
                raise WebSocketException(code=1008, reason="Too many connections from this IP")
            if client_ip != "unknown":
                self._ip_counts[client_ip] += 1

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
                            "ts": __import__("datetime")
                            .datetime.now(__import__("datetime").UTC)
                            .isoformat(),
                            "source": "system",
                        },
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

            client_ip = websocket.client.host if websocket.client else "unknown"
            if client_ip != "unknown" and self._ip_counts[client_ip] > 0:
                self._ip_counts[client_ip] -= 1

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
                # Add 1s timeout to drop slow clients instead of blocking everyone
                await asyncio.wait_for(ws.send_text(message), timeout=1.0)
            except TimeoutError:
                # Graceful degradation: Client too slow, drop this frame
                logger.warning("Broadcast dropped frame due to client backpressure timeout")
            except Exception:
                dead.append(ws)

        if dead:
            for ws in dead:
                await self.disconnect(ws)

    async def send_personal(self, websocket: WebSocket, data: Any) -> None:
        """Send a JSON message to a specific WebSocket connection with backpressure handling."""
        message = json.dumps(data) if not isinstance(data, str) else data
        try:
            # 1s timeout prevents a slow client from blocking the pubsub consumer loop
            await asyncio.wait_for(websocket.send_text(message), timeout=1.0)
        except TimeoutError:
            logger.warning("send_personal dropped frame due to client backpressure timeout")
        except Exception as e:
            # Re-raise to let caller handle disconnects
            raise e

    @property
    def active_channels(self) -> list[str]:
        """Return list of channels with active connections."""
        return list(self._channels.keys())

    def channel_count(self, channel: str) -> int:
        """Return the number of active connections on a channel."""
        return len(self._channels.get(channel, set()))


# Singleton instance used across the application
ws_manager = ConnectionManager()
