"""WebSocket endpoints for prices, signals, alerts, and backtest progress."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Import MarketDataService for real quotes
from app.services.market_data_service import MarketDataService

# Import prediction engine for real signal streaming
from app.services.prediction_engine import get_full_prediction

# Logging
from app.core.logging import get_logger
logger = get_logger(__name__)

from app.websocket.connection_manager import get_connection_manager

router = APIRouter(prefix="/ws")

# In-process signal cache: symbol -> (result_dict, fetched_at_timestamp)
_signal_cache: dict[str, tuple[dict, float]] = {}
_SIGNAL_CACHE_TTL = 60.0  # seconds


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
    """WebSocket route for live prices and signals.
    
    Subscribes to Redis 'prices.ticks' channel and forwards updates for
    symbols that the client has explicitly subscribed to.
    """
    await websocket.accept()
    subscribed_symbols: set[str] = set()

    from app.database.redis_client import get_redis_client
    import json
    
    redis_client = await get_redis_client()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("prices.ticks")

    async def read_client_messages():
        try:
            while True:
                payload = await websocket.receive_json()
                action = str(payload.get("action", "")).lower()
                symbols = [str(s).upper().strip() for s in payload.get("symbols", [])]
                if action == "subscribe":
                    subscribed_symbols.update(symbols)
                    logger.info(f"ws_prices: client subscribed to symbols={symbols}")
                    for sym in symbols:
                        try:
                            q = await MarketDataService.get_quote(sym)
                            if q and q.get("price") is not None:
                                await websocket.send_json({
                                    "type": "tick",
                                    "symbol": q["symbol"],
                                    "price": float(q["price"]),
                                    "change": float(q.get("change", 0.0)),
                                    "change_pct": float(q.get("change_pct", 0.0)),
                                    "timestamp": datetime.now(UTC).isoformat(),
                                })
                        except Exception as q_err:
                            logger.debug(f"Error sending initial quote snapshot for {sym}: {q_err}")
                elif action == "unsubscribe":
                    subscribed_symbols.difference_update(symbols)
                    logger.info(f"ws_prices: client unsubscribed from symbols={symbols}")
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.debug(f"Error reading client message: {e}")

    async def send_price_ticks():
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                payload_raw = message.get("data")
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                
                symbol = str(payload.get("symbol", "")).upper().strip()
                # Check normal symbol and symbol without exchange suffix (e.g. RELIANCE.NS vs RELIANCE)
                symbol_base = symbol.split(".")[0]
                
                if symbol in subscribed_symbols or symbol_base in subscribed_symbols:
                    await websocket.send_json(payload)
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.debug(f"Error sending ticks to client: {e}")

    t1 = asyncio.create_task(read_client_messages())
    t2 = asyncio.create_task(send_price_ticks())
    try:
        await asyncio.gather(t1, t2)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"ws_prices connection error: {e}")
    finally:
        t1.cancel()
        t2.cancel()
        try:
            await pubsub.unsubscribe("prices.ticks")
            await pubsub.close()
        except Exception:
            pass


@router.websocket("/signals")
async def ws_signals(websocket: WebSocket):
    """Stream real signal_update messages from the 7-layer prediction engine.

    Each subscribed symbol is computed via get_full_prediction (with a 60s in-process
    cache). Symbols where the engine returns is_computed=False are skipped — never
    replaced with random data.
    """
    manager = get_connection_manager()
    channel = "signals:global"
    await manager.connect(websocket, channel)
    subscribed_symbols: set[str] = set()
    try:
        while True:
            # Receive subscription messages with a 2-second timeout
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=2.0)
                action = str(payload.get("action", "")).lower()
                symbols = [str(s).upper() for s in payload.get("symbols", [])]
                if action == "subscribe":
                    subscribed_symbols.update(symbols)
                elif action == "unsubscribe":
                    subscribed_symbols.difference_update(symbols)
            except (TimeoutError, asyncio.TimeoutError):
                pass

            now_ts = asyncio.get_event_loop().time()

            for symbol in sorted(subscribed_symbols):
                # Check in-process cache
                cached = _signal_cache.get(symbol)
                if cached and (now_ts - cached[1]) < _SIGNAL_CACHE_TTL:
                    result = cached[0]
                else:
                    try:
                        result = await get_full_prediction(symbol)
                        if result and result.get("is_computed", False):
                            _signal_cache[symbol] = (result, now_ts)
                    except Exception as e:
                        logger.debug("ws_signals_prediction_error symbol=%s error=%s", symbol, str(e))
                        result = None

                if not result or not result.get("is_computed", False):
                    # Skip — no random fallback ever
                    continue

                ens = result.get("ensemble", {})
                direction = ens.get("direction", "NEUTRAL")
                signal_score = ens.get("raw_ensemble", 0.0)
                confidence = ens.get("confidence", 0.5)

                try:
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "signal_update",
                            "symbol": symbol,
                            "signal": round(float(signal_score), 4),
                            "confidence": round(float(confidence), 4),
                            "direction": direction,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception as e:
                    logger.debug("ws_signals_send_error symbol=%s error=%s", symbol, str(e))

            if not subscribed_symbols:
                await manager.send_personal(
                    websocket,
                    {"type": "heartbeat", "channel": "signals", "timestamp": datetime.now(UTC).isoformat()},
                )

            # Rate-limit: avoid hammering the prediction engine
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@router.websocket("/alerts")
async def ws_alerts(websocket: WebSocket):
    manager = get_connection_manager()
    await manager.connect(websocket, "signals:alerts")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "signals:alerts")


@router.websocket("/backtest-progress")
async def ws_backtest_progress(websocket: WebSocket):
    from app.api.v1.backtest import BACKTEST_PROGRESS
    from app.models.backtest import BacktestJob
    from app.database.connection import async_session_factory
    from sqlalchemy import select
    from uuid import UUID

    manager = get_connection_manager()
    channel = "backtest:progress"
    await manager.connect(websocket, channel)
    
    subscribed_job_id = None
    
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if isinstance(msg, dict) and msg.get("action") == "subscribe":
                    subscribed_job_id = msg.get("job_id")
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            if not subscribed_job_id:
                if BACKTEST_PROGRESS:
                    subscribed_job_id = list(BACKTEST_PROGRESS.keys())[-1]
                else:
                    async with async_session_factory() as session:
                        stmt = select(BacktestJob).order_by(BacktestJob.created_at.desc()).limit(1)
                        res = await session.execute(stmt)
                        job = res.scalar_one_or_none()
                        if job:
                            subscribed_job_id = str(job.id)

            if subscribed_job_id:
                pct = BACKTEST_PROGRESS.get(subscribed_job_id)
                if pct is None:
                    try:
                        job_uuid = UUID(subscribed_job_id)
                        async with async_session_factory() as session:
                            stmt = select(BacktestJob).where(BacktestJob.id == job_uuid)
                            res = await session.execute(stmt)
                            job = res.scalar_one_or_none()
                            if job:
                                if job.status in ("COMPLETED", "DONE"):
                                    pct = 100
                                elif job.status == "FAILED":
                                    pct = 100
                                else:
                                    pct = 0
                            else:
                                pct = 0
                    except Exception:
                        pct = 0

                await manager.send_personal(
                    websocket,
                    {
                        "type": "progress",
                        "job_id": subscribed_job_id,
                        "pct": pct,
                        "current_date": datetime.now(UTC).date().isoformat(),
                        "equity_value": round(1_000_000 * (1 + pct / 1000), 2),
                    },
                )
                if pct >= 100:
                    await asyncio.sleep(2.0)
            else:
                await manager.send_personal(
                    websocket,
                    {"type": "heartbeat", "channel": "backtest", "timestamp": datetime.now(UTC).isoformat()},
                )
                await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
