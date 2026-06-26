"""Async Redis connection utilities and caching helpers.

Provides:
- Singleton Redis connection pool management
- Key-value caching with TTL
- Pub/Sub message handling
- Automatic reconnection and error recovery
- Health check utilities

Redis is used for:
- Session caching (access/refresh tokens)
- Feature vector caching (TTL-based)
- Rate limiting counters
- Pub/Sub broadcasting (prices, signals)
- Celery message broker and result backend
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ─── Singleton Pool ───────────────────────────────────────────────────────

class InMemoryPubSub:
    """Mock pubsub subscription implementation for offline/fallback mode."""
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        self.subscribed_channels: set[str] = set()
        self.queue: asyncio.Queue = asyncio.Queue()

    async def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self.subscribed_channels.add(ch)
        self.cache.active_pubsubs.add(self)

    async def unsubscribe(self, *channels: str) -> None:
        for ch in channels:
            self.subscribed_channels.discard(ch)
        if not self.subscribed_channels:
            self.cache.active_pubsubs.discard(self)

    async def close(self) -> None:
        self.cache.active_pubsubs.discard(self)

    async def listen(self):
        while True:
            try:
                msg = await self.queue.get()
                yield msg
            except asyncio.CancelledError:
                break


class InMemoryCache:
    """Simple in‑memory mock implementing a subset of Redis methods used in the app.
    Stores values in a dict; methods are async for compatibility.
    """
    def __init__(self):
        self.store: dict[str, any] = {}
        self.active_pubsubs: set[InMemoryPubSub] = set()

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: any, ex: int | None = None) -> bool:
        self.store[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: any) -> bool:
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        return int(self.store.pop(key, None) is not None)

    async def publish(self, channel: str, message: str) -> int:
        count = 0
        for ps in list(self.active_pubsubs):
            if channel in ps.subscribed_channels:
                await ps.queue.put({
                    "type": "message",
                    "channel": channel,
                    "data": message
                })
                count += 1
        return count

    def pubsub(self) -> InMemoryPubSub:
        return InMemoryPubSub(self)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self.store.clear()
        self.active_pubsubs.clear()


_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None
_redis_lock = asyncio.Lock()


async def _redis_pool_singleton() -> Redis:
    """Get or create singleton Redis connection pool.

    Uses double-checked locking pattern for thread-safe lazy initialization.
    Creates a single shared connection pool across all requests.

    Returns:
        Redis: Async Redis client from singleton pool.

    Raises:
        ConnectionError: If unable to connect to Redis server.

    Example:
        redis = await _redis_pool_singleton()
        value = await redis.get("key")
    """
    global _redis_client, _redis_pool

    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    async with _redis_lock:
        # Double-check after acquiring lock
        if _redis_client is not None:
            return _redis_client

        try:
            _redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            _redis_client = Redis(connection_pool=_redis_pool)

            # Test connection
            await _redis_client.ping()

            logger.info(
                "redis_client_initialized",
                redis_url=settings.REDIS_URL.split("@")[1]
                if "@" in settings.REDIS_URL
                else "***",
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            return _redis_client

        except Exception as e:
            logger.warning("Redis connection failed, falling back to in-memory cache: %s", str(e))
            _redis_client = InMemoryCache()
            return _redis_client


async def get_redis_client() -> Redis:
    """Get Redis async client (alias for _redis_pool_singleton).

    Provides clean API for getting Redis client in dependency injection.

    Returns:
        Redis: Async Redis client.

    Raises:
        ConnectionError: If unable to connect.

    Example:
        from app.core.dependencies import get_redis

        @app.get("/cache")
        async def get_cache(redis: Annotated[Redis, Depends(get_redis)]):
            value = await redis.get("key")
            return value
    """
    return await _redis_pool_singleton()


async def get_redis() -> Redis:
    """Compatibility alias for legacy imports expecting get_redis."""
    return await get_redis_client()


async def close_redis() -> None:
    """Close Redis connection pool.

    Should be called during application shutdown.

    Args:
        None

    Returns:
        None

    Raises:
        None: Exceptions are logged but suppressed.
    """
    global _redis_client, _redis_pool

    try:
        if _redis_client:
            await _redis_client.close()
            logger.info("redis_client_closed")
    except Exception as e:
        logger.warning("redis_close_error: %s", str(e))
    finally:
        _redis_client = None
        _redis_pool = None


# ─── Cache Helpers ────────────────────────────────────────────────────────
async def cache_get(
    redis: Redis,
    key: str,
    default: Any = None,
) -> Any:
    """Get value from Redis cache with JSON deserialization.

    Args:
        redis: Redis client instance.
        key: Cache key.
        default: Default value if key doesn't exist.

    Returns:
        The cached value (JSON-deserialized) or default.

    Raises:
        None: Exceptions are logged and default is returned.

    Example:
        value = await cache_get(redis, "user:123", default={})
    """
    try:
        value = await redis.get(key)
        if value is None:
            return default

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value  # Return as string if not JSON

    except Exception as e:
        logger.warning("cache_get_error key=%s error=%s", key, str(e))
        return default


async def cache_set(
    redis: Redis,
    key: str,
    value: Any,
    ttl: timedelta | None = None,
) -> bool:
    """Set value in Redis cache with JSON serialization.

    Args:
        redis: Redis client instance.
        key: Cache key.
        value: Value to cache (will be JSON-serialized if dict/list).
        ttl: Time-to-live duration (None = no expiration).

    Returns:
        bool: True if set successfully, False otherwise.

    Raises:
        None: Exceptions are logged and False is returned.

    Example:
        success = await cache_set(
            redis,
            "user:123",
            {"id": "123", "email": "user@example.com"},
            ttl=timedelta(hours=1)
        )
    """
    try:
        # Serialize value
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)

        # Set with or without TTL
        if ttl:
            ttl_seconds = int(ttl.total_seconds())
            result = await redis.setex(key, ttl_seconds, serialized)
        else:
            result = await redis.set(key, serialized)

        return bool(result)

    except Exception as e:
        logger.warning("cache_set_error key=%s error=%s", key, str(e))
        return False


async def cache_delete(redis: Redis, key: str) -> bool:
    """Delete value from Redis cache.

    Args:
        redis: Redis client instance.
        key: Cache key to delete.

    Returns:
        bool: True if key existed and was deleted.

    Raises:
        None: Exceptions are logged and False is returned.
    """
    try:
        result = await redis.delete(key)
        return bool(result)
    except Exception as e:
        logger.warning("cache_delete_error key=%s error=%s", key, str(e))
        return False


async def cache_exists(redis: Redis, key: str) -> bool:
    """Check if key exists in Redis cache.

    Args:
        redis: Redis client instance.
        key: Cache key to check.

    Returns:
        bool: True if key exists.

    Raises:
        None: Exceptions are logged and False is returned.
    """
    try:
        result = await redis.exists(key)
        return bool(result)
    except Exception as e:
        logger.warning("cache_exists_error key=%s error=%s", key, str(e))
        return False


# ─── Publish/Subscribe Helpers ────────────────────────────────────────────
async def publish_message(
    redis: Redis,
    channel: str,
    message: dict[str, Any],
) -> int:
    """Publish message to Redis Pub/Sub channel.

    Args:
        redis: Redis client instance.
        channel: Channel name to publish to.
        message: Message dict (will be JSON-serialized).

    Returns:
        int: Number of subscribers that received the message.

    Raises:
        None: Exceptions are logged and 0 is returned.

    Example:
        subscribers = await publish_message(
            redis,
            "prices:AAPL",
            {"price": 150.25, "timestamp": 1234567890}
        )
    """
    try:
        serialized = json.dumps(message)
        count = await redis.publish(channel, serialized)
        logger.debug(
            "message_published",
            channel=channel,
            subscribers=count,
            message_size=len(serialized),
        )
        return count
    except Exception as e:
        logger.warning("publish_message_error channel=%s error=%s", channel, str(e))
        return 0


# ─── Health Check ────────────────────────────────────────────────────────
async def get_redis_health() -> dict[str, Any]:
    """Check Redis server health and pool status.

    Args:
        None

    Returns:
        dict: {
            "connected": bool,
            "server_info": dict or str,
            "memory_used_mb": float,
            "connected_clients": int,
        }

    Raises:
        None: Returns partial health info even if checks fail.
    """
    health = {
        "connected": False,
        "server_info": None,
        "memory_used_mb": 0,
        "connected_clients": 0,
    }

    try:
        redis = await _redis_pool_singleton()
        await redis.ping()
        health["connected"] = True

        # Get server info
        info = await redis.info()
        if info:
            health["server_info"] = {
                "redis_version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
            }
            # Memory is in bytes
            memory_bytes = info.get("used_memory", 0)
            health["memory_used_mb"] = round(memory_bytes / (1024 * 1024), 2)
            health["connected_clients"] = info.get("connected_clients", 0)

    except Exception as e:
        logger.warning("redis_health_check_error: %s", str(e))

    return health

