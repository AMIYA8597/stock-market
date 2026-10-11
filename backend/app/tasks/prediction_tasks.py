"""Celery periodic task for ML predictions during NSE market hours."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from celery import shared_task

logger = logging.getLogger(__name__)

NSE_OPEN_HOUR = 9
NSE_OPEN_MINUTE = 15
NSE_CLOSE_HOUR = 15
NSE_CLOSE_MINUTE = 30

DEFAULT_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"]


def _is_market_hours(now: datetime | None = None) -> bool:
    """Check if current time is within NSE trading hours (9:15-15:30 IST, weekdays)."""
    import zoneinfo

    if now is None:
        now = datetime.now(UTC)

    ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    ist_now = now.astimezone(ist)

    if ist_now.weekday() >= 5:
        return False

    market_open = ist_now.replace(
        hour=NSE_OPEN_HOUR, minute=NSE_OPEN_MINUTE, second=0, microsecond=0,
    )
    market_close = ist_now.replace(
        hour=NSE_CLOSE_HOUR, minute=NSE_CLOSE_MINUTE, second=0, microsecond=0,
    )
    return market_open <= ist_now <= market_close


@shared_task(name="run_periodic_predictions", bind=True, max_retries=0)
def run_periodic_predictions(self: object) -> dict:
    """Run ML predictions for all tracked symbols. Skips outside market hours."""
    if not _is_market_hours():
        logger.info("Outside NSE market hours, skipping predictions")
        return {"status": "skipped", "reason": "outside_market_hours"}

    results = {}
    for symbol in DEFAULT_SYMBOLS:
        try:
            result = _run_single_prediction(symbol)
            results[symbol] = result
        except Exception:
            logger.exception("Prediction failed for %s", symbol)
            results[symbol] = {"status": "error"}

    return {"status": "completed", "predictions": results}


def _run_single_prediction(symbol: str) -> dict:
    """Run prediction for a single symbol, store result, and broadcast via WebSocket."""
    import asyncio

    from app.services.prediction_engine import get_full_prediction

    loop = asyncio.new_event_loop()
    try:
        prediction = loop.run_until_complete(get_full_prediction(symbol))
    finally:
        loop.close()

    try:
        _store_prediction(symbol, prediction)
    except Exception:
        logger.exception("Failed to store prediction for %s", symbol)

    try:
        _broadcast_prediction(symbol, prediction)
    except Exception:
        logger.exception("Failed to broadcast prediction for %s", symbol)

    return {
        "symbol": symbol,
        "signal": prediction.get("ensemble_signal"),
        "confidence": prediction.get("confidence"),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _store_prediction(symbol: str, prediction: dict) -> None:
    """Store prediction in the database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.models.prediction import MLPrediction

    settings = get_settings()
    sync_url = str(settings.DATABASE_URL).replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        record = MLPrediction(
            symbol=symbol,
            model_name="ensemble_v1",
            time=datetime.now(UTC),
            raw_signal=prediction.get("ensemble_signal", 0.0),
            p50_return=prediction.get("expected_return_pct", 0.0),
        )
        session.add(record)
        session.commit()


def _broadcast_prediction(symbol: str, prediction: dict) -> None:
    """Push prediction to connected WebSocket clients."""
    try:
        import json

        from app.services.websocket_manager import manager

        message = json.dumps({
            "type": "prediction",
            "symbol": symbol,
            "data": {
                "signal": prediction.get("ensemble_signal"),
                "confidence": prediction.get("confidence"),
                "regime": prediction.get("regime"),
                "timestamp": datetime.now(UTC).isoformat(),
                "data_source": prediction.get("data_source", "yfinance"),
            },
        })
        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.broadcast(message))
        loop.close()
    except ImportError:
        logger.debug("WebSocket manager not available")
