import re

with open('backend/app/core/websocket_manager.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_init = '''    def __init__(self) -> None:
        # Maps channel name -> set of WebSockets
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # Maps WebSocket -> set of channel names it is subscribed to
        self._subscriptions: dict[WebSocket, set[str]] = defaultdict(set)
        # Maps WebSocket -> background heartbeat task
        self._heartbeats: dict[WebSocket, asyncio.Task] = {}
        # Maps IP -> count of active connections
        self._ip_counts: dict[str, int] = defaultdict(int)
        self.MAX_CONNECTIONS_PER_IP = 30
        self._lock = asyncio.Lock()
        
        self._redis_task: asyncio.Task | None = None

    async def startup(self):
        """Start the Redis subscriber loop."""
        if self._redis_task is None:
            self._redis_task = asyncio.create_task(self._redis_listener())
            
    async def shutdown(self):
        """Stop the Redis subscriber loop."""
        if self._redis_task:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
            
    async def _redis_listener(self):
        from app.database.redis_client import get_redis_client
        import json
        try:
            redis_client = await get_redis_client()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ws_broadcasts")
            try:
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    try:
                        payload_raw = message.get("data")
                        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                        channel = payload.get("channel")
                        data = payload.get("data")
                        if channel and data:
                            await self._local_broadcast(channel, data)
                    except Exception as e:
                        logger.debug(f"Error processing ws_broadcasts message: {e}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Redis listener error: {e}")
            finally:
                try:
                    await pubsub.unsubscribe("ws_broadcasts")
                    await pubsub.close()
                except:
                    pass
        except Exception as e:
            logger.debug(f"Redis listener outer error: {e}")
'''

code = re.sub(r'    def __init__\(self\) -> None:.*?self\._lock = asyncio\.Lock\(\)', new_init, code, flags=re.DOTALL)

new_broadcast = '''    async def broadcast(self, channel: str, data: Any) -> None:
        """Publish a broadcast message to Redis so all workers get it."""
        from app.database.redis_client import get_redis_client
        import json
        try:
            redis_client = await get_redis_client()
            payload = json.dumps({"channel": channel, "data": data})
            await redis_client.publish("ws_broadcasts", payload)
        except Exception as e:
            logger.warning(f"Failed to publish broadcast to redis: {e}")
            # Fallback to local broadcast if redis fails
            await self._local_broadcast(channel, data)

    async def _local_broadcast(self, channel: str, data: Any) -> None:'''

code = code.replace('    async def broadcast(self, channel: str, data: Any) -> None:', new_broadcast)

with open('backend/app/core/websocket_manager.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched websocket_manager.py')
