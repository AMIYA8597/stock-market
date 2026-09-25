# backend/app/services/alert_engine.py
"""Alert Engine – evaluates stock predictions and user alerts from SQLAlchemy to fire updates."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import and_, select

from app.database.connection import async_session_factory
from app.models.alerts import Alert
from app.models.instrument import Instrument

from app.services.signal_engine import TechnicalSignalEngine

logger = logging.getLogger(__name__)

ALERT_THRESHOLDS = {
    "STRONG_BUY": {"min_score": 0.40, "min_confidence": 0.70},
    "BUY": {"min_score": 0.18, "min_confidence": 0.60},
    "STRONG_SELL": {"min_score": -0.40, "min_confidence": 0.70},
    "SELL": {"min_score": -0.18, "min_confidence": 0.60},
}


async def _get_signal_for_alert(symbol: str) -> dict:
    from app.database.connection import async_session_factory
    from sqlalchemy import select
    from app.models.market import Instrument, OHLCV
    
    async with async_session_factory() as session:
        inst_res = await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        inst = inst_res.scalars().first()
        if not inst:
            raise ValueError(f"No history available for {symbol}")
            
        ohlcv_res = await session.execute(
            select(OHLCV)
            .where((OHLCV.instrument_id == inst.id) & (OHLCV.interval == '1d'))
            .order_by(OHLCV.timestamp.asc())
        )
        bars = ohlcv_res.scalars().all()
        
        if not bars:
            raise ValueError(f"No history available for {symbol}")
            
        hist = []
        for b in bars:
            hist.append({
                'time': b.timestamp.timestamp(),
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': float(b.volume)
            })

    df = pd.DataFrame(hist)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])

    res = TechnicalSignalEngine.generate_signal(df)
    res["current_price"] = df.iloc[-1]["close"]
    return res


async def check_and_fire_alerts(symbols: list[str], websocket_manager) -> list[dict]:
    fired = []

    # 1. Fetch technical signals
    results = await asyncio.gather(
        *[_get_signal_for_alert(s) for s in symbols], return_exceptions=True
    )
    prediction_map = {}

    for symbol, result in zip(symbols, results, strict=False):
        if isinstance(result, Exception):
            logger.warning(f"Failed to get signal for symbol={symbol} in alert check: {result}")
            continue
        prediction_map[symbol.upper()] = result

    # 2. Check and trigger general system thresholds
    for symbol, result in prediction_map.items():
        direction = result["direction"]
        score = result["score"]
        confidence = result["confidence"]
        price = result["current_price"]

        threshold = ALERT_THRESHOLDS.get(direction)
        if not threshold:
            continue

        if abs(score) >= abs(threshold["min_score"]) and confidence >= threshold["min_confidence"]:
            system_alert = {
                "type": "signal_alert",
                "symbol": symbol,
                "direction": direction,
                "signal_score": round(score, 4),
                "confidence": round(confidence, 4),
                "current_price": price,
                "patterns": result.get("patterns", []),
                "timestamp": datetime.now(UTC).isoformat(),
                "message": f"SYSTEM ALERT: {direction} signal for {symbol} at ₹{price:.2f} (confidence: {confidence:.0%})",
            }
            fired.append(system_alert)
            try:
                await websocket_manager.broadcast("signals:alerts", system_alert)
            except Exception as e:
                logger.warning(f"Failed to broadcast system alert: {e}")

    # 3. Check user subscriptions in SQLAlchemy
    try:
        async with async_session_factory() as db:
            stmt = (
                select(Alert, Instrument.symbol)
                .outerjoin(Instrument, Alert.symbol_id == Instrument.id)
                .where(and_(Alert.enabled, not Alert.is_triggered))
            )
            res = await db.execute(stmt)
            active_alerts = res.all()

            for alert_obj, ticker in active_alerts:
                if not ticker:
                    continue
                alert_symbol = ticker.upper()
                if alert_symbol not in prediction_map:
                    continue

                pred = prediction_map[alert_symbol]
                price = float(pred["current_price"])
                direction = pred["direction"].upper()

                alert_type = alert_obj.alert_type
                threshold = float(alert_obj.threshold) if alert_obj.threshold is not None else 0.0
                trigger_fired = False
                trigger_message = ""

                if alert_type == "PRICE_ABOVE" and price > threshold:
                    trigger_fired = True
                    trigger_message = f"PRICE ALERT: {alert_symbol} crossed ABOVE ₹{threshold:.2f} (Current: ₹{price:.2f})"
                elif alert_type == "PRICE_BELOW" and price < threshold:
                    trigger_fired = True
                    trigger_message = f"PRICE ALERT: {alert_symbol} crossed BELOW ₹{threshold:.2f} (Current: ₹{price:.2f})"
                elif alert_type == "SIGNAL_CHANGE" and direction == alert_obj.name.upper():
                    trigger_fired = True
                    trigger_message = f"SIGNAL ALERT: {alert_symbol} generated signal {direction}"

                if trigger_fired:
                    # Update status in SQLAlchemy
                    alert_obj.is_triggered = True
                    alert_obj.triggered_at = datetime.now(UTC)
                    await db.commit()

                    user_alert_payload = {
                        "type": "user_alert",
                        "alert_id": str(alert_obj.id),
                        "user_id": str(alert_obj.user_id),
                        "symbol": alert_symbol,
                        "alert_type": alert_type,
                        "threshold": threshold,
                        "current_price": price,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": trigger_message,
                    }
                    fired.append(user_alert_payload)

                    # Broadcast to user alerts channel
                    try:
                        await websocket_manager.broadcast(f"alerts:{alert.user_id}", user_alert_payload)
                        logger.info(f"User alert triggered & broadcasted: {trigger_message}")
                    except Exception as b_err:
                        logger.warning(f"Failed to broadcast user alert: {b_err}")

                    # Here we could fire SMTP emails as well using SMTP_SERVER env vars.

    except Exception as sqla_err:
        logger.warning(f"Error querying active user alert subscriptions in SQLAlchemy: {sqla_err}")

    return fired
