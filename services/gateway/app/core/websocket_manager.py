"""
WebSocket connection manager for real-time data streaming.
"""

import asyncio
import json
from typing import Dict, List, Optional, Set

import redis.asyncio as redis
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = structlog.get_logger()


class ConnectionManager:
    """
    WebSocket connection manager with Redis pub/sub for scaling.
    """

    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.redis_pubsub: Optional[redis.Redis] = None
        self.pubsub_task: Optional[asyncio.Task] = None

    async def startup(self):
        """
        Initialize Redis pub/sub for cross-instance communication.
        """
        if settings.ENABLE_WEBSOCKETS:
            self.redis_pubsub = redis.from_url(
                settings.REDIS_URL,
                db=settings.REDIS_DB_WS,
                decode_responses=True,
            )

            # Start pub/sub listener
            self.pubsub_task = asyncio.create_task(self._listen_pubsub())

            logger.info("WebSocket manager started")

    async def shutdown(self):
        """
        Cleanup connections and Redis.
        """
        # Close all active connections
        for user_connections in self.active_connections.values():
            for websocket in user_connections.values():
                try:
                    await websocket.close()
                except Exception:
                    pass

        self.active_connections.clear()

        # Stop pub/sub task
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass

        # Close Redis
        if self.redis_pubsub:
            await self.redis_pubsub.close()

        logger.info("WebSocket manager shutdown")

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """
        Accept WebSocket connection and track it.
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}

        # Check connection limit per user
        if len(self.active_connections[user_id]) >= settings.RATE_LIMIT_WS_CONNECTIONS_PER_USER:
            await websocket.send_json({
                "type": "error",
                "message": "Maximum WebSocket connections per user exceeded",
            })
            await websocket.close(code=1008)  # Policy violation
            return

        self.active_connections[user_id][connection_id] = websocket

        logger.info(
            "WebSocket connection established",
            user_id=user_id,
            connection_id=connection_id,
            total_connections=sum(len(conns) for conns in self.active_connections.values()),
        )

    async def disconnect(self, user_id: str, connection_id: str):
        """
        Remove WebSocket connection.
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(connection_id, None)

            # Clean up empty user dict
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(
            "WebSocket connection closed",
            user_id=user_id,
            connection_id=connection_id,
        )

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send message to all connections of a specific user.
        """
        if user_id not in self.active_connections:
            return

        disconnected = []
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send WebSocket message",
                    user_id=user_id,
                    connection_id=connection_id,
                    error=str(e),
                )
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(user_id, connection_id)

    async def broadcast(self, message: dict, channel: str = "global"):
        """
        Broadcast message to all connected users.
        """
        if self.redis_pubsub:
            # Publish to Redis for cross-instance broadcasting
            await self.redis_pubsub.publish(channel, json.dumps(message))

        # Send to local connections
        disconnected_users = []
        for user_id, user_connections in self.active_connections.items():
            disconnected_connections = []
            for connection_id, websocket in user_connections.items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        "Failed to broadcast WebSocket message",
                        user_id=user_id,
                        connection_id=connection_id,
                        error=str(e),
                    )
                    disconnected_connections.append(connection_id)

            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                await self.disconnect(user_id, connection_id)

            if not self.active_connections.get(user_id):
                disconnected_users.append(user_id)

        # Clean up empty user dicts
        for user_id in disconnected_users:
            self.active_connections.pop(user_id, None)

    async def broadcast_to_users(self, message: dict, user_ids: List[str]):
        """
        Broadcast message to specific users.
        """
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

    async def _listen_pubsub(self):
        """
        Listen for Redis pub/sub messages from other instances.
        """
        if not self.redis_pubsub:
            return

        pubsub = self.redis_pubsub.pubsub()
        await pubsub.subscribe("websocket_broadcast")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._handle_pubsub_message(data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in pub/sub message")
        except Exception as e:
            logger.error("Pub/sub listener error", error=str(e))

    async def _handle_pubsub_message(self, message: dict):
        """
        Handle incoming pub/sub message.
        """
        # Broadcast to local connections
        await self.broadcast(message, channel="local_only")


# Global WebSocket manager instance
websocket_manager = ConnectionManager()