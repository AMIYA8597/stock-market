# backend/app/infrastructure/market_data/router.py
"""Market data service using free providers with caching.

Provides REST endpoint `/api/v1/market/quote/{symbol}` and WebSocket `/api/v1/market/ws/quotes`.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.dependencies import get_redis_optional
from app.providers.market_data_provider import MarketDataProvider, get_is_market_closed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market")

settings = get_settings()
CACHE_TTL = 300  # seconds


class QuoteResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    price: float = Field(..., description="Current price")
    timestamp: datetime = Field(..., description="Quote timestamp (UTC)")
    source: str = Field(..., description="Provider that supplied the data")
    market_closed: bool = Field(False, description="True if market is currently closed")


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
            "market_closed": get_is_market_closed()
        }
        if redis:
            await set_cached_quote(redis, symbol, result)
        return QuoteResponse(symbol=symbol, **result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to fetch quote for {symbol}: {exc}",
        )


# Centralized WebSocket manager for broadcasting quotes to subscribed clients
class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}
        self._broadcaster_task: asyncio.Task | None = None
        self._redis = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        self.subscriptions[ws] = set()

        # Start broadcaster if not running
        if self._broadcaster_task is None or self._broadcaster_task.done():
            self._broadcaster_task = asyncio.create_task(self.broadcast_loop())

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        self.subscriptions.pop(ws, None)

    async def send(self, ws: WebSocket, data: dict):
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            self.disconnect(ws)

    def set_redis(self, redis):
        self._redis = redis

    async def broadcast_loop(self):
        while True:
            try:
                if not self.connections:
                    await asyncio.sleep(5)
                    continue

                # Gather all unique symbols currently subscribed by anyone
                all_symbols = set()
                for syms in self.subscriptions.values():
                    all_symbols.update(syms)

                if not all_symbols:
                    await asyncio.sleep(5)
                    continue

                # Fetch quotes for all unique symbols concurrently
                async def _fetch_safe(sym):
                    try:
                        quote = await get_quote(sym, self._redis)
                        # We use isoformat to serialize datetime correctly
                        data = quote.dict()
                        data["timestamp"] = data["timestamp"].isoformat()
                        return data
                    except Exception as exc:
                        return {"symbol": sym, "error": str(exc)}

                fetch_tasks = {
                    sym: asyncio.create_task(_fetch_safe(sym))
                    for sym in all_symbols
                }

                # Wait for all fetches to complete
                if fetch_tasks:
                    await asyncio.wait(fetch_tasks.values())

                # Broadcast to each connection its subscribed symbols
                for ws in list(self.connections):
                    subs = self.subscriptions.get(ws, set())
                    for sym in subs:
                        task = fetch_tasks.get(sym)
                        if task and task.done():
                            res = task.result()
                            if res:
                                asyncio.create_task(self.send(ws, res))

                # Sleep before next tick (if market is closed, we could sleep longer, but this is simple enough)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Broadcaster loop error: {exc}")
                await asyncio.sleep(5)

manager = WSManager()


@router.websocket("/ws/quotes")
async def ws_quotes(ws: WebSocket, redis=Depends(get_redis_optional)):
    manager.set_redis(redis)
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
                symbols = {s.upper() for s in payload.get("symbols", [])}
                manager.subscriptions[ws] = symbols
            except Exception:
                await manager.send(ws, {"error": "Invalid subscription message"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)

