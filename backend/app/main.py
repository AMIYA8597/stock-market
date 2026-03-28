"""
QuantEdge — FastAPI Application Entry Point.

Configures CORS, mounts API v1 router, and registers WebSocket endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.events import shutdown_events, startup_events
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, parse_rate_limit
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

# ─── CORS Middleware ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, config=parse_rate_limit(settings.DEFAULT_RATE_LIMIT))

# ─── Mount API v1 ─────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router)
