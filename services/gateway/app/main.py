"""
NeuroQuant Gateway Service
FastAPI microservice providing unified REST + WebSocket API gateway
for the NeuroQuant institutional-grade stock market platform.

Features:
- Enterprise-grade authentication (RS256 JWT, Argon2id, TOTP 2FA)
- Rate limiting with Redis sliding window
- RBAC with granular permissions
- Comprehensive audit logging
- WebSocket real-time streaming
- Input validation and sanitization
- Security headers and CORS
- Health monitoring and metrics
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.audit_logger import AuditLogger
from app.core.config import settings
from app.core.database import create_tables, engine
from app.core.rate_limiter import CustomLimiter
from app.core.websocket_manager import websocket_manager
from app.utils.logging import setup_logging

# Setup structured logging
setup_logging()

# Initialize audit logger
audit_logger = AuditLogger()

# Initialize rate limiter
limiter = CustomLimiter(key_func=get_remote_address)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger = structlog.get_logger()
    logger.info("Starting NeuroQuant Gateway Service")

    # Create database tables
    await create_tables()

    # Initialize WebSocket manager
    await websocket_manager.startup()

    # Initialize audit logger
    await audit_logger.startup()

    logger.info(
        "Gateway service started successfully",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG
    )

    yield

    # Shutdown
    logger.info("Shutting down NeuroQuant Gateway Service")

    # Cleanup WebSocket connections
    await websocket_manager.shutdown()

    # Cleanup audit logger
    await audit_logger.shutdown()

    # Close database connections
    await engine.dispose()

    logger.info("Gateway service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="NeuroQuant Gateway API",
    description="Unified REST + WebSocket API gateway for NeuroQuant institutional-grade stock market platform",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    """
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' wss: https:; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp

    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (production only)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    """
    logger = structlog.get_logger()
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method,
        client_ip=get_remote_address(request),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "neuroquant-gateway",
        "version": settings.VERSION,
        "timestamp": asyncio.get_event_loop().time(),
    }

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "NeuroQuant Gateway API",
        "version": settings.VERSION,
        "description": "Unified REST + WebSocket API gateway for institutional-grade stock market platform",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None,  # Use our custom logging
    )