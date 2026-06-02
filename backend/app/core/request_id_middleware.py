"""Request ID middleware for distributed tracing.

Injects a unique request ID into every request, allowing you to trace
a single request through all logs, databases, external APIs, etc.

The request ID is:
1. Extracted from X-Request-ID header if present
2. Generated as UUID v4 if not provided
3. Set in response headers for client tracking
4. Stored in context variables for automatic log injection
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.structured_logging import (
    get_logger,
    request_id_var,
    user_email_var,
    user_id_var,
)

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request ID into every request for correlation & tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request context and response headers."""
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
        request_id_var.set(request_id)

        # Extract user info from auth if available
        try:
            if hasattr(request.state, "user"):
                user = request.state.user
                if isinstance(user, dict):
                    user_id_var.set(user.get("sub") or user.get("user_id"))
                    user_email_var.set(user.get("email"))
        except Exception:
            pass  # User not yet available in request lifecycle

        # Time the request
        start_time = time.monotonic()

        # Call the endpoint
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Add request ID and tracing headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        # Log request completion
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


class CORSProductionMiddleware(BaseHTTPMiddleware):
    """Production-safe CORS configuration.

    In production, CORS origins must be explicitly whitelisted.
    Defaults to denying all CORS requests unless env variables set.
    """

    def __init__(self, app, allowed_origins: list[str] | None = None):
        """Initialize CORS middleware.

        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins. If None, none allowed.
        """
        super().__init__(app)
        self.allowed_origins = allowed_origins or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check CORS origin before processing request."""
        origin = request.headers.get("origin")

        # Preflight requests
        if request.method == "OPTIONS":
            if origin and origin in self.allowed_origins:
                return Response(
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,PATCH",
                        "Access-Control-Allow-Headers": "Content-Type,Authorization",
                        "Access-Control-Max-Age": "86400",
                    },
                )
            else:
                return Response(status_code=403)  # Forbidden

        # Regular requests
        response = await call_next(request)

        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
