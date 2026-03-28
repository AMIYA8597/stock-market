"""WebSocket endpoints for prices, signals, alerts, and backtest progress."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from random import Random

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.connection_manager import get_connection_manager

router = APIRouter(prefix="/ws")


def _seed(key: str) -> int:
    return int(sha256(key.encode("utf-8")).hexdigest()[:8], 16)


@router.websocket("/market/{symbol}")
async def ws_market_feed(websocket: WebSocket, symbol: str):
    manager = get_connection_manager()
    channel = f"market:{symbol.upper()}"
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/portfolio")
async def ws_portfolio_feed(websocket: WebSocket):
    manager = get_connection_manager()
    channel = "portfolio:live"
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/prices")
async def ws_prices(websocket: WebSocket):
    manager = get_connection_manager()
    channel = "prices:global"
    await manager.connect(websocket, channel)
    subscribed_symbols: set[str] = set()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                action = str(payload.get("action", "")).lower()
                symbols = [str(s).upper() for s in payload.get("symbols", [])]
                if action == "subscribe":
                    subscribed_symbols.update(symbols)
                elif action == "unsubscribe":
                    subscribed_symbols.difference_update(symbols)
            except TimeoutError:
                pass

            for symbol in sorted(subscribed_symbols):
                rng = Random(_seed(symbol))
                await manager.send_personal(
                    websocket,
                    {
                        "type": "tick",
                        "symbol": symbol,
                        "price": round(100 + rng.random() * 1500, 2),
                        "change_pct": round(-2 + rng.random() * 4, 3),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
            if not subscribed_symbols:
                await manager.send_personal(
                    websocket,
                    {"type": "heartbeat", "channel": "prices", "timestamp": datetime.now(UTC).isoformat()},
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/signals")
async def ws_signals(websocket: WebSocket):
    manager = get_connection_manager()
    channel = "signals:global"
    await manager.connect(websocket, channel)
    subscribed_symbols: set[str] = set()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                action = str(payload.get("action", "")).lower()
                symbols = [str(s).upper() for s in payload.get("symbols", [])]
                if action == "subscribe":
                    subscribed_symbols.update(symbols)
                elif action == "unsubscribe":
                    subscribed_symbols.difference_update(symbols)
            except TimeoutError:
                pass

            for symbol in sorted(subscribed_symbols):
                rng = Random(_seed(f"signal:{symbol}"))
                score = rng.uniform(-1, 1)
                direction = "BUY" if score > 0.2 else "SELL" if score < -0.2 else "NEUTRAL"
                await manager.send_personal(
                    websocket,
                    {
                        "type": "signal_update",
                        "symbol": symbol,
                        "signal": round(score, 4),
                        "confidence": round(0.55 + rng.random() * 0.4, 4),
                        "direction": direction,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
            if not subscribed_symbols:
                await manager.send_personal(
                    websocket,
                    {"type": "heartbeat", "channel": "signals", "timestamp": datetime.now(UTC).isoformat()},
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/alerts")
async def ws_alerts(websocket: WebSocket):
    manager = get_connection_manager()
    channel = "alerts:global"
    await manager.connect(websocket, channel)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
            except TimeoutError:
                pass
            await manager.send_personal(
                websocket,
                {
                    "type": "alert_triggered",
                    "alert_id": "ALRT-001",
                    "message": "Signal flipped to BUY for RELIANCE.NS",
                    "symbol": "RELIANCE.NS",
                    "value": 0.67,
                },
            )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/backtest-progress")
async def ws_backtest_progress(websocket: WebSocket):
    manager = get_connection_manager()
    channel = "backtest:progress"
    await manager.connect(websocket, channel)
    progress = 0
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except TimeoutError:
                pass
            progress = min(progress + 10, 100)
            await manager.send_personal(
                websocket,
                {
                    "type": "progress",
                    "job_id": "BT-2026-001",
                    "pct": progress,
                    "current_date": datetime.now(UTC).date().isoformat(),
                    "equity_value": round(1_000_000 * (1 + progress / 1000), 2),
                },
            )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
