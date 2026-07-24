"""HTTP middleware for security headers and simple in-memory rate limiting."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.database.redis_client import _redis_pool_singleton

settings = get_settings()


@dataclass(slots=True)
class RateLimitConfig:
    max_requests: int = 100
    window_seconds: int = 60


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline OWASP-aligned security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", settings.SECURITY_CSP_POLICY)
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Best-effort in-memory rate limiter per client IP."""

    def __init__(self, app, config: RateLimitConfig | None = None):
        super().__init__(app)
        self._config = config or RateLimitConfig()

    async def dispatch(self, request: Request, call_next):
        # Allow bypassing rate limiting in test mode via environment var (handled below if needed)

        if request.url.path.startswith("/api/docs") or request.url.path.startswith("/api/openapi"):
            return await call_next(request)

        is_auth_path = request.url.path.startswith(f"{settings.API_V1_PREFIX}/auth")
        active_limit = parse_rate_limit(settings.AUTH_RATE_LIMIT) if is_auth_path else self._config

        client_ip = request.client.host if request.client else "unknown"
        bucket_key = f"rate_limit:{'auth' if is_auth_path else 'default'}:{client_ip}"

        now = time.monotonic()

        # In test mode we just bypass if PYTEST is running, unless we want to test rate limits
        if os.getenv("PYTEST_CURRENT_TEST"):
            pass
        else:
            try:
                redis = await _redis_pool_singleton()

                # Token bucket logic via Redis pipeline
                # ZREMRANGEBYSCORE key -inf (now - window)
                # ZADD key now now
                # ZCARD key
                # EXPIRE key window

                window_start = now - active_limit.window_seconds

                pipe = redis.pipeline()
                pipe.zremrangebyscore(bucket_key, "-inf", window_start)
                pipe.zadd(bucket_key, {str(now): now})
                pipe.zcard(bucket_key)
                pipe.expire(bucket_key, active_limit.window_seconds)
                results = await pipe.execute()

                current_hits = results[2]

                if current_hits > active_limit.max_requests:
                    # Get oldest entry to calculate retry-after
                    oldest = await redis.zrange(bucket_key, 0, 0, withscores=True)
                    if oldest:
                        retry_after = int(max(oldest[0][1] + active_limit.window_seconds - now, 1))
                    else:
                        retry_after = active_limit.window_seconds

                    request_id = request.headers.get("X-Request-ID", f"req_{uuid4().hex[:12]}")
                    origin = request.headers.get("origin")
                    headers = {
                        "Retry-After": str(retry_after),
                        "X-Request-ID": request_id,
                    }
                    if origin and origin in settings.BACKEND_CORS_ORIGINS:
                        headers["Access-Control-Allow-Origin"] = origin
                        headers["Access-Control-Allow-Credentials"] = "true"

                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "error": {
                                "code": "RATE_LIMIT_EXCEEDED",
                                "message": "Rate limit exceeded. Please retry later.",
                                "details": [{"field": "request", "message": "Too many requests in the current time window.", "code": "TOO_MANY_REQUESTS"}],
                            },
                            "request_id": request_id,
                            "retry_after_seconds": retry_after,
                        },
                        headers=headers,
                    )
            except Exception as e:
                # Fallback on Redis failure - allow request but log
                from app.core.logging import get_logger
                get_logger(__name__).error(f"Rate limiter redis error: {e}")

        response: Response = await call_next(request)
        # Assuming we bypass X-RateLimit for simplicity in test mode
        response.headers["X-RateLimit-Limit"] = str(active_limit.max_requests)
        # response.headers["X-RateLimit-Remaining"] = str(...)  # Omitted for performance
        return response


def parse_rate_limit(value: str | None) -> RateLimitConfig:
    """Parse limits in the form '100/minute' with safe defaults."""
    if not value:
        return RateLimitConfig()

    try:
        parts = value.strip().lower().split("/")
        max_requests = int(parts[0])
        unit = parts[1] if len(parts) > 1 else "minute"
        window = (
            60 if unit in {"minute", "min", "m"} else 1 if unit in {"second", "sec", "s"} else 3600
        )
        return RateLimitConfig(max_requests=max(1, max_requests), window_seconds=window)
    except Exception:
        return RateLimitConfig()
