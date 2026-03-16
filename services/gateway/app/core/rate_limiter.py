"""
Custom rate limiter with Redis sliding window algorithm.
"""

import asyncio
import time
from typing import Optional

import redis.asyncio as redis
import structlog
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = structlog.get_logger()


class RedisSlidingWindowLimiter:
    """
    Redis-based sliding window rate limiter.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.script = self.redis.register_script("""
            local key = KEYS[1]
            local window = tonumber(ARGV[1])
            local limit = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])

            -- Remove old entries outside the window
            redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

            -- Count remaining entries
            local count = redis.call('ZCARD', key)

            if count < limit then
                -- Add new entry
                redis.call('ZADD', key, now, now)
                -- Set expiry on the key
                redis.call('EXPIRE', key, window)
                return 1
            else
                return 0
            end
        """)

    async def is_allowed(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> bool:
        """
        Check if request is allowed under rate limit.
        """
        now = int(time.time() * 1000)  # milliseconds
        result = await self.script(keys=[key], args=[window_seconds * 1000, max_requests, now])
        return result == 1

    async def get_remaining_requests(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> int:
        """
        Get remaining requests in current window.
        """
        now = int(time.time() * 1000)
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, now - (window_seconds * 1000))
        # Count remaining
        count = await self.redis.zcard(key)
        return max(0, max_requests - count)

    async def get_reset_time(self, key: str, window_seconds: int) -> Optional[float]:
        """
        Get time when rate limit resets.
        """
        # Get oldest timestamp in window
        result = await self.redis.zrange(key, 0, 0, withscores=True)
        if result:
            oldest_timestamp = result[0][1] / 1000  # Convert back to seconds
            return oldest_timestamp + window_seconds
        return None


class CustomLimiter:
    """
    Custom rate limiter with multiple tiers and Redis backend.
    """

    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB_RATE_LIMIT,
            decode_responses=True,
        )
        self.sliding_limiter = RedisSlidingWindowLimiter(self.redis)

    async def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[str] = None,
        endpoint: str = "default",
    ) -> dict:
        """
        Check rate limit for request.

        Returns:
            dict: {
                "allowed": bool,
                "remaining": int,
                "reset_time": float,
                "retry_after": int
            }
        """
        # Determine rate limit based on endpoint
        if "/auth/" in str(request.url):
            max_requests = settings.RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE
            window_seconds = 60
        elif "/predictions/" in str(request.url):
            max_requests = settings.RATE_LIMIT_ML_REQUESTS_PER_HOUR
            window_seconds = 3600
        else:
            max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
            window_seconds = 60

        # Create rate limit key
        client_ip = get_remote_address(request)
        if user_id:
            key = f"ratelimit:user:{user_id}:{endpoint}"
        else:
            key = f"ratelimit:ip:{client_ip}:{endpoint}"

        # Check if allowed
        allowed = await self.sliding_limiter.is_allowed(key, window_seconds, max_requests)

        if allowed:
            remaining = await self.sliding_limiter.get_remaining_requests(
                key, window_seconds, max_requests
            )
            reset_time = await self.sliding_limiter.get_reset_time(key, window_seconds)

            return {
                "allowed": True,
                "remaining": remaining - 1,  # Subtract current request
                "reset_time": reset_time,
                "retry_after": 0,
            }
        else:
            reset_time = await self.sliding_limiter.get_reset_time(key, window_seconds)
            retry_after = int(reset_time - time.time()) if reset_time else window_seconds

            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                user_id=user_id,
                endpoint=endpoint,
                retry_after=retry_after,
            )

            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": retry_after,
            }

    async def cleanup(self):
        """
        Cleanup Redis connections.
        """
        await self.redis.close()


# Global limiter instance
limiter = CustomLimiter()

# SlowAPI compatible limiter
slowapi_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    storage_options={"db": settings.REDIS_DB_RATE_LIMIT},
)