"""
QuantEdge — FastAPI Application Entry Point.

Configures CORS, mounts API v1 router, and registers WebSocket endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.websocket_manager import ws_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    logger.info("🚀 QuantEdge API starting up...")
    yield
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

# ─── Mount API v1 ─────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ─── WebSocket Endpoints ──────────────────────────────────

@app.websocket("/ws/market/{symbol}")
async def ws_market_feed(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for live market price streaming.

    Clients subscribe to a symbol channel and receive real-time tick updates.
    """
    channel = f"market:{symbol.upper()}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            # Keep connection alive; actual data is pushed by the data pipeline
            data = await websocket.receive_text()
            logger.debug(f"WS received from {channel}: {data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)


@app.websocket("/ws/portfolio")
async def ws_portfolio_feed(websocket: WebSocket):
    """WebSocket endpoint for live portfolio P&L updates."""
    channel = "portfolio:live"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)


@app.websocket("/ws/alerts")
async def ws_alerts_feed(websocket: WebSocket):
    """WebSocket endpoint for real-time alert notifications."""
    channel = "alerts:live"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)
