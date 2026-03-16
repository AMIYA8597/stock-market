"""
Redis client configuration.
"""

import redis.asyncio as redis
from app.core.config import settings


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )


# Redis connection pools for different purposes
redis_cache = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_CACHE_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

redis_pubsub = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_PUBSUB_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

redis_sessions = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_SESSIONS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)