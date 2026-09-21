import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.schema import schema_guard

settings = get_settings()

class SchemaGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow health routes
        if request.url.path.startswith("/health") or request.url.path.startswith("/api/v1/health") or request.url.path == "/":
            return await call_next(request)

        # Optional local dev disable flag
        if os.environ.get("DISABLE_SCHEMA_GUARD", "false").lower() == "true":
            return await call_next(request)

        guard_result = await schema_guard()
        if guard_result["schema"] == "mismatch":
            return JSONResponse(
                status_code=503,
                content={"detail": "SCHEMA_MISMATCH", "info": guard_result}
            )

        return await call_next(request)
