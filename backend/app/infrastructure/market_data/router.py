# backend/app/infrastructure/market_data/router.py
"""Market data service using free providers with caching.

Provides REST endpoint `/api/v1/market/quote/{symbol}` and WebSocket `/api/v1/market/ws/quotes`.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.dependencies import get_redis_optional
from app.providers.market_data_provider import MarketDataProvider

router = APIRouter(prefix="/market")

settings = get_settings()
CACHE_TTL = 300  # seconds


class QuoteResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    price: float = Field(..., description="Current price")
    timestamp: datetime = Field(..., description="Quote timestamp (UTC)")
    source: str = Field(..., description="Provider that supplied the data")


async def get_cached_quote(redis, symbol: str) -> dict[str, Any] | None:
    raw = await redis.get(f"quote:{symbol}")
    if raw:
        try:
            payload = json.loads(raw)
            payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
            return payload
        except Exception:
            return None
    return None


async def set_cached_quote(redis, symbol: str, payload: dict[str, Any]):
    payload_copy = payload.copy()
    payload_copy["timestamp"] = payload_copy["timestamp"].isoformat()
    await redis.setex(f"quote:{symbol}", CACHE_TTL, json.dumps(payload_copy))


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str, redis=Depends(get_redis_optional)) -> QuoteResponse:
    symbol = symbol.upper()
    if redis:
        cached = await get_cached_quote(redis, symbol)
        if cached:
            return QuoteResponse(symbol=symbol, **cached)
    try:
        candles = await MarketDataProvider.get_candle(symbol, interval="1m", period="1d")
        if not candles:
            raise RuntimeError("No candle data")
        latest = candles[-1]
        result = {
            "price": latest.close,
            "timestamp": datetime.utcfromtimestamp(latest.timestamp),
            "source": "market_data_provider",
        }
        if redis:
            await set_cached_quote(redis, symbol, result)
        return QuoteResponse(symbol=symbol, **result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to fetch quote for {symbol}: {exc}",
        )


# Simple WebSocket manager for broadcasting quotes to subscribed clients
class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, list[str]] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        self.subscriptions[ws] = []

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        self.subscriptions.pop(ws, None)

    async def send(self, ws: WebSocket, data: dict):
        await ws.send_text(json.dumps(data))


manager = WSManager()


@router.websocket("/ws/quotes")
async def ws_quotes(ws: WebSocket, redis=Depends(get_redis_optional)):
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
                symbols = [s.upper() for s in payload.get("symbols", [])]
                manager.subscriptions[ws] = symbols
            except Exception:
                await manager.send(ws, {"error": "Invalid subscription message"})
                continue
            # Push updates every 5 s for this connection's subscriptions
            while True:
                for sym in manager.subscriptions[ws]:
                    try:
                        quote = await get_quote(sym, redis)
                        await manager.send(ws, quote.dict())
                    except Exception as exc:
                        await manager.send(ws, {"symbol": sym, "error": str(exc)})
                await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
        raise
