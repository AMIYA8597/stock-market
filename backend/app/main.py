"""
QuantEdge — FastAPI Application Entry Point.

Configures CORS, mounts API v1 router, and registers WebSocket endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository's `backend` directory is on sys.path so sibling
# top-level packages like `research` (located at backend/research)
# are importable when the server is started from the repository root.
_backend_root = Path(__file__).resolve().parent.parent
_backend_root_str = str(_backend_root)
if _backend_root_str not in sys.path:
    sys.path.insert(0, _backend_root_str)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger

# Import (and thereby activate as Celery's "current app") our configured Celery
# instance before any task modules load. Task files use the generic @shared_task
# decorator, which binds to whatever Celery app is current at call time — if this
# app was never imported anywhere in the process, Celery silently falls back to a
# default instance with no broker configured (defaults to amqp://localhost, which
# isn't running here), instead of our Redis-backed, dev-eager-mode-enabled app.
from app.core.celery_app import celery_app as _celery_app  # noqa: F401

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ImportError:  # pragma: no cover
    sentry_sdk = None
    FastApiIntegration = None

import logging as _logging

# Suppress noisy third-party library logs
for _noisy_lib in ("yfinance", "urllib3", "urllib3.connectionpool", "peewee"):
    _logging.getLogger(_noisy_lib).setLevel(_logging.WARNING)


import time

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.events import shutdown_events, startup_events
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.request_id_middleware import RequestIDMiddleware
from app.core.structured_logging import configure_logging
from app.database.connection import async_session_factory
from app.database.redis_client import InMemoryCache, get_redis_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register scheduled tasks after the API object exists so optional research
    # dependencies cannot block liveness or documentation startup.
    try:
        from app.tasks import retraining_trigger as _retraining_trigger_tasks  # noqa: F401
    except Exception as exc:
        logger.warning("scheduled_task_registration_deferred", error=str(exc))
    background_tasks = await startup_events()
    yield
    await shutdown_events(background_tasks)
    logger.info("🛑 QuantEdge API shutting down...")


def create_app() -> FastAPI:
    _app = FastAPI(
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

    if settings.RATE_LIMIT_ENABLED:
        _app.add_middleware(RateLimitMiddleware)

    _app.add_middleware(SecurityHeadersMiddleware)

    if settings.ALLOWED_HOSTS:
        _app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    _app.add_middleware(RequestIDMiddleware)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        # Dev preview tooling assigns an arbitrary free localhost port when 3000
        # is already taken (e.g. by another session's dev server) — a fixed
        # origin list would break CORS every time that happens. Regex is scoped
        # to localhost/127.0.0.1 only and skipped outside development.
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$"
        if settings.ENVIRONMENT == "development"
        else None,
        allow_credentials=True,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    register_exception_handlers(_app)

    # ─── Mount Routers ─────────────────────────────────────────
    _app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @_app.get("/liveness", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "running"}

    @_app.get("/readiness", tags=["health"])
    async def readiness() -> dict[str, str]:
        try:
            from sqlalchemy import text

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            return {"status": "not_ready", "database": "unavailable"}
        return {"status": "ready", "database": "ok"}

    # Health check endpoint. Provider diagnostics are intentionally excluded:
    # this endpoint must remain cheap and must not make external market calls.
    from app.core.schema import schema_guard
    @_app.get("/health")
    async def health_check():
        start_time = time.time()
        health_status = {
            "status": "healthy",
            "db": "ok",
            "redis": "ok",
            "providers": "ok",
            "uptime_seconds": 0.0,
        }

        # Check DB
        try:
            from sqlalchemy import text

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            health_status["db"] = "unhealthy"
            health_status["status"] = "degraded"

        # Check Redis
        try:
            redis = await get_redis_client()
            if isinstance(redis, InMemoryCache):
                # get_redis_client() silently swaps in a process-local dict when
                # real Redis is unreachable, so a bare ping() would report "ok"
                # even though caching/pubsub isn't actually shared or persistent.
                health_status["redis"] = "degraded_in_memory_fallback"
                health_status["status"] = "degraded"
            elif not await redis.ping():
                raise ValueError("Redis ping returned false")
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["redis"] = "unhealthy"
            health_status["status"] = "degraded"

        schema_res = await schema_guard()
        health_status.update(schema_res)
        if schema_res["schema"] == "mismatch":
            health_status["status"] = "mismatch"
        health_status["uptime_seconds"] = round(time.time() - start_time, 3)
        return health_status

    return _app


app = create_app()
