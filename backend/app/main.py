"""
QuantEdge — FastAPI Application Entry Point.

Configures CORS, mounts API v1 router, and registers WebSocket endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ImportError:  # pragma: no cover
    sentry_sdk = None
    FastApiIntegration = None

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.events import shutdown_events, startup_events
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, parse_rate_limit
from app.core.request_id_middleware import RequestIDMiddleware
from app.core.structured_logging import configure_logging
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

# ─── Mount API v1 ─────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router)
