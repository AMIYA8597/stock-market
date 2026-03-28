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
import logging
from datetime import timedelta
from typing import Any, Optional

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Singleton Pool ───────────────────────────────────────────────────────
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None
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
            logger.error("redis_initialization_error: %s", str(e), exc_info=True)
            raise ConnectionError(f"Failed to initialize Redis: {e}") from e


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
    ttl: Optional[timedelta] = None,
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

