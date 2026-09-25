"""WebSocket endpoints for prices, signals, alerts, and backtest progress."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Logging
from app.core.logging import get_logger

# Import MarketDataService for real quotes
from app.services.market_data_service import MarketDataService

# Import prediction engine for real signal streaming
from app.services.prediction_engine import get_full_prediction

logger = get_logger(__name__)

from app.websocket.connection_manager import get_connection_manager

router = APIRouter(prefix="/ws")




# Removed dead ws_portfolio_feed route (unused)
# @router.websocket("/portfolio")
# async def ws_portfolio_feed(websocket: WebSocket):
#     manager = get_connection_manager()
#     channel = "portfolio:live"
#     await manager.connect(websocket, channel)
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         await manager.disconnect(websocket, channel)


@router.websocket("/prices")
async def ws_prices(websocket: WebSocket, ticket: str = ""):
    from app.websocket.ws_auth import authenticate_ws
    user_id = await authenticate_ws(websocket, ticket)
    if not user_id: return
    """WebSocket route for live prices and signals."""
    manager = get_connection_manager()
    await manager.connect(websocket)
    subscribed_symbols: set[str] = set()

    import json

    from app.database.redis_client import get_redis_client

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
                    logger.info(f"ws_prices: client subscribed to symbols={symbols}")
                    for sym in symbols:
                        if sym not in subscribed_symbols:
                            subscribed_symbols.add(sym)
                            await manager.subscribe(websocket, f"market:{sym}")
                            count = await redis_client.hincrby("active_symbol_counts", sym, 1)
                            if count == 1:
                                await redis_client.sadd("active_symbols", sym)

                        try:
                            q = await MarketDataService.get_quote(sym)
                            if q and q.get("price") is not None:
                                await manager.send_personal(
                                    websocket,
                                    {
                                        "type": "tick",
                                        "symbol": q["symbol"],
                                        "payload": {
                                            "price": float(q["price"]),
                                            "change": float(q.get("change", 0.0)),
                                            "change_pct": float(q.get("change_pct", 0.0)),
                                        },
                                        "ts": datetime.now(UTC).isoformat(),
                                        "source": q.get("source", "yfinance"),
                                    },
                                )
                        except Exception as q_err:
                            logger.debug(f"Error sending initial quote snapshot for {sym}: {q_err}")
                elif action == "unsubscribe":
                    for sym in symbols:
                        if sym in subscribed_symbols:
                            subscribed_symbols.remove(sym)
                            await manager.unsubscribe(websocket, f"market:{sym}")
                            count = await redis_client.hincrby("active_symbol_counts", sym, -1)
                            if count <= 0:
                                await redis_client.srem("active_symbols", sym)
                                await redis_client.hdel("active_symbol_counts", sym)
                    logger.info(f"ws_prices: client unsubscribed from symbols={symbols}")
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
                    await manager.send_personal(websocket, payload)
        except Exception as e:
            logger.debug(f"Error sending ticks to client: {e}")

    t1 = asyncio.create_task(read_client_messages())
    t2 = asyncio.create_task(send_price_ticks())
    try:
        # read_client_messages() only exits once the client actually disconnects;
        # send_price_ticks() only exits when a send to a dead socket fails, which
        # can never happen if no ticks arrive (e.g. market closed) — wait for
        # whichever finishes first and cancel the other, instead of gather()
        # which would leak this connection (and its per-IP slot) forever.
        await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"ws_prices connection error: {e}")
    finally:
        t1.cancel()
        t2.cancel()
        try:
            for sym in list(subscribed_symbols):
                count = await redis_client.hincrby("active_symbol_counts", sym, -1)
                if count <= 0:
                    await redis_client.srem("active_symbols", sym)
                    await redis_client.hdel("active_symbol_counts", sym)
        except Exception as e:
            logger.debug(f"Error decrementing active symbols on disconnect: {e}")

        try:
            await pubsub.unsubscribe("prices.ticks")
            await pubsub.close()
        except Exception:
            pass
        await manager.disconnect(websocket)


@router.websocket("/signals")
async def ws_signals(websocket: WebSocket, ticket: str = ""):
    from app.websocket.ws_auth import authenticate_ws
    user_id = await authenticate_ws(websocket, ticket)
    if not user_id: return
    """Stream real signal_update messages from the 7-layer prediction engine.

    Each subscribed symbol is computed via get_full_prediction (with a 60s in-process
    cache). Instruments where the engine returns is_computed=False are skipped — never
    replaced with random data.
    """
    manager = get_connection_manager()
    await manager.connect(websocket)
    channel = "signals:global"
    await manager.subscribe(websocket, channel)
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
            except TimeoutError:
                pass
            except Exception:
                pass

            now_ts = asyncio.get_event_loop().time()

            for symbol in sorted(subscribed_symbols):
                from app.database.redis_client import get_redis, cache_get, cache_set
                redis = await get_redis()
                result = await cache_get(redis, f"ws:signal:{symbol}")
                if not result:
                    try:
                        result = await get_full_prediction(symbol)
                        if result and result.get("is_computed", False):
                            from datetime import timedelta
                            await cache_set(redis, f"ws:signal:{symbol}", result, ttl=timedelta(seconds=60))
                    except Exception as e:
                        logger.debug("ws_signals_prediction_error symbol=%s error=%s", symbol, str(e))
                        result = None

                if not result or not result.get("is_computed", False):
                    continue

                ens = result.get("ensemble", {})
                direction = ens.get("direction", "NEUTRAL")
                signal_score = ens.get("raw_ensemble", 0.0)
                confidence = ens.get("confidence", 0.5)

                try:
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "signal",
                            "symbol": symbol,
                            "payload": {
                                "signal": round(float(signal_score), 4),
                                "confidence": round(float(confidence), 4),
                                "direction": direction,
                            },
                            "ts": datetime.now(UTC).isoformat(),
                            "source": "system",
                        },
                    )
                except Exception as e:
                    logger.debug("ws_signals_send_error symbol=%s error=%s", symbol, str(e))

            # Rate-limit: avoid hammering the prediction engine
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


@router.websocket("/alerts")
async def ws_alerts(websocket: WebSocket, ticket: str = ""):
    from app.websocket.ws_auth import authenticate_ws
    user_id = await authenticate_ws(websocket, ticket)
    if not user_id: return
    manager = get_connection_manager()
    await manager.connect(websocket)
    await manager.subscribe(websocket, f"alerts:{user_id}")
    await manager.subscribe(websocket, "signals:alerts")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


@router.websocket("/backtest-progress")
async def ws_backtest_progress(websocket: WebSocket, ticket: str):
    from uuid import UUID

    from sqlalchemy import select

    from app.api.v1.backtest import BACKTEST_PROGRESS
    from app.database.connection import async_session_factory
    from app.models.backtest import BacktestJob

    from app.websocket.ws_auth import authenticate_ws
    user_id_str = await authenticate_ws(websocket, ticket)
    if not user_id_str:
        return

    manager = get_connection_manager()
    await manager.connect(websocket)
    channel = "backtest:progress"
    await manager.subscribe(websocket, channel)

    subscribed_job_id = None

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if isinstance(msg, dict) and msg.get("action") == "subscribe":
                    requested_job_id = msg.get("job_id")
                    if requested_job_id:
                        # Verify ownership
                        try:
                            job_uuid = UUID(requested_job_id)
                            async with async_session_factory() as session:
                                stmt = select(BacktestJob).where(
                                    BacktestJob.id == job_uuid,
                                    BacktestJob.user_id == UUID(user_id_str)
                                )
                                res = await session.execute(stmt)
                                job = res.scalar_one_or_none()
                                if job:
                                    subscribed_job_id = requested_job_id
                        except Exception:
                            pass
            except TimeoutError:
                pass
            except Exception:
                pass

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
                        "symbol": None,
                        "payload": {
                            "job_id": subscribed_job_id,
                            "pct": pct,
                            "current_date": datetime.now(UTC).date().isoformat(),
                            "equity_value": round(1_000_000 * (1 + pct / 1000), 2),
                        },
                        "ts": datetime.now(UTC).isoformat(),
                        "source": "system",
                    },
                )
                if pct >= 100:
                    await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)




@router.websocket("/stream")
async def ws_stream(websocket: WebSocket, ticket: str = ""):
    from app.api.v1.websocket_url import _WS_TICKETS
    user_id = _WS_TICKETS.pop(ticket, None)
    if not user_id:
        await websocket.close(code=1008)
        return
        
    manager = get_connection_manager()
    await manager.connect(websocket)
    
    # Subscribe to personal alerts by default
    await manager.subscribe(websocket, f"alerts:{user_id}")
    await manager.subscribe(websocket, "signals:alerts")
    
    # Track subscriptions for this unified connection
    subscribed_symbols: set[str] = set()
    
    try:
        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                action = str(payload.get("action", "")).lower()
                channel = str(payload.get("channel", "")).lower()
                symbols = [str(s).upper() for s in payload.get("symbols", [])]
                
                if action == "subscribe":
                    if channel == "prices":
                        for symbol in symbols:
                            await manager.subscribe(websocket, f"prices:{symbol}")
                    elif channel == "signals":
                        subscribed_symbols.update(symbols)
                elif action == "unsubscribe":
                    if channel == "prices":
                        for symbol in symbols:
                            await manager.unsubscribe(websocket, f"prices:{symbol}")
                    elif channel == "signals":
                        subscribed_symbols.difference_update(symbols)
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            # Stream signals for subscribed symbols
            if subscribed_symbols:
                for symbol in sorted(subscribed_symbols):
                    from app.database.redis_client import get_redis, cache_get, cache_set
                    redis = await get_redis()
                    result = await cache_get(redis, f"ws:signal:{symbol}")
                    if not result:
                        try:
                            from app.services.prediction_engine import get_full_prediction
                            result = await get_full_prediction(symbol)
                            if result and result.get("is_computed", False):
                                from datetime import timedelta
                                await cache_set(redis, f"ws:signal:{symbol}", result, ttl=timedelta(seconds=60))
                        except Exception as e:
                            logger.debug("ws_signals_prediction_error symbol=%s error=%s", symbol, str(e))
                            result = None

                    if not result or not result.get("is_computed", False):
                        continue

                    ens = result.get("ensemble", {})
                    direction = ens.get("direction", "NEUTRAL")
                    signal_score = ens.get("raw_ensemble", 0.0)
                    confidence = ens.get("confidence", 0.5)

                    try:
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "signal",
                                "symbol": symbol,
                                "payload": {
                                    "signal": round(float(signal_score), 4),
                                    "confidence": round(float(confidence), 4),
                                    "direction": direction,
                                },
                                "ts": datetime.now(UTC).isoformat(),
                                "source": "system",
                            },
                        )
                    except Exception:
                        pass
                
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
