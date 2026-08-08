import time
from fastapi import HTTPException
from app.database.redis_client import _redis_pool_singleton
from app.core.test_state import is_test_mode
from app.core.logging import get_logger

logger = get_logger(__name__)

async def check_rate_limit(key: str, requests: int, window: int) -> None:
    """Check if the given key has exceeded the rate limit.
    Raises HTTPException(429) if exceeded.
    """
    if is_test_mode():
        return

    bucket_key = f"rate_limit:{key}"
    now = time.monotonic()
    window_start = now - window

    try:
        redis = await _redis_pool_singleton()
        pipe = redis.pipeline()
        pipe.zremrangebyscore(bucket_key, "-inf", window_start)
        pipe.zadd(bucket_key, {str(now): now})
        pipe.zcard(bucket_key)
        pipe.expire(bucket_key, window)
        results = await pipe.execute()

        if results[2] > requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("redis_rate_limit_error", error=str(e))
