"""Async Redis connection utilities."""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Return a shared async Redis client instance."""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
