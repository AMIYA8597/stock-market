"""HTTP middleware for security headers and simple in-memory rate limiting."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


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
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Best-effort in-memory rate limiter per client IP."""

    def __init__(self, app, config: RateLimitConfig | None = None):
        super().__init__(app)
        self._config = config or RateLimitConfig()
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/docs") or request.url.path.startswith("/api/openapi"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self._config.window_seconds

        async with self._lock:
            bucket = self._hits[client_ip]
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= self._config.max_requests:
                retry_after = int(max(bucket[0] + self._config.window_seconds - now, 1))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please retry later.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._config.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(self._config.max_requests - len(self._hits[client_ip]), 0))
        return response


def parse_rate_limit(value: str | None) -> RateLimitConfig:
    """Parse limits in the form '100/minute' with safe defaults."""
    if not value:
        return RateLimitConfig()

    try:
        parts = value.strip().lower().split("/")
        max_requests = int(parts[0])
        unit = parts[1] if len(parts) > 1 else "minute"
        window = 60 if unit in {"minute", "min", "m"} else 1 if unit in {"second", "sec", "s"} else 3600
        return RateLimitConfig(max_requests=max(1, max_requests), window_seconds=window)
    except Exception:
        return RateLimitConfig()
