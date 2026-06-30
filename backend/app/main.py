"""
QuantEdge — FastAPI Application Entry Point.

Configures CORS, mounts API v1 router, and registers WebSocket endpoints.
"""

from __future__ import annotations

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ImportError:  # pragma: no cover
    sentry_sdk = None
    FastApiIntegration = None

import logging as _logging
# Suppress noisy third-party library logs
for _noisy_lib in ("pymongo", "motor", "yfinance", "urllib3", "urllib3.connectionpool", "peewee"):
    _logging.getLogger(_noisy_lib).setLevel(_logging.WARNING)


from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.events import shutdown_events, startup_events
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, parse_rate_limit
from app.core.request_id_middleware import RequestIDMiddleware
from app.core.structured_logging import configure_logging
from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from app.websocket.router import router as websocket_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    logger.info("🚀 QuantEdge API starting up...")
    background_tasks = await startup_events()
    yield
    await shutdown_events(background_tasks)
    logger.info("🛑 QuantEdge API shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Stock Market Intelligence System",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

setup_logging()
configure_logging(settings.ENVIRONMENT)

if settings.SENTRY_DSN and sentry_sdk is not None and FastApiIntegration is not None:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )

# ─── CORS Middleware ───────────────────────────────────────
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

if settings.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

app.add_middleware(SecurityHeadersMiddleware)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, config=parse_rate_limit(settings.DEFAULT_RATE_LIMIT))


def _error_code_for_status(status_code: int) -> ErrorCode:
    mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        409: ErrorCode.ALREADY_EXISTS,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        location = error.get("loc") or []
        field = ".".join(str(part) for part in location if part not in {"body", "query", "path", "header"}) or None
        details.append(
            ErrorDetail(
                field=field,
                message=error.get("msg", "Invalid value"),
                code=str(error.get("type", "invalid_request")).upper(),
            )
        )

    payload = ErrorResponse.create(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation failed. Please check your input.",
        details=details,
    ).dict()
    return JSONResponse(status_code=400, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"success", "error", "request_id"}.issubset(exc.detail.keys()):
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)

    code = _error_code_for_status(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    payload = ErrorResponse.create(code=code, message=message).dict()
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)

# ─── Mount API v1 ─────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router)

# ─── Mount QuantEdge specific router ──────────────────────
from app.api.quantedge_router import router as quantedge_router
app.include_router(quantedge_router)

