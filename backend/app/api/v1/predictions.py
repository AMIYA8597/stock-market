"""ML prediction and signal API endpoints."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf

from app.core.database import get_db
from app.schemas.prediction import ForecastRequest
from app.services.intelligence_service import intelligence_service

router = APIRouter()


async def _get_current_price(symbol: str, db: AsyncSession) -> float:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT o.close
                    FROM ohlcv o
                    JOIN symbols s ON s.id = o.symbol_id
                    WHERE UPPER(s.ticker) = :ticker
                    ORDER BY o.time DESC
                    LIMIT 1
                    """
                ),
                {"ticker": symbol.upper()},
            )
        ).mappings().first()
        if row is not None:
            latest_close = float(row["close"])
            if latest_close > 0:
                return latest_close
    except Exception:
        pass

    def _fetch() -> float:
        ticker = yf.Ticker(symbol)
        fast_info = getattr(ticker, "fast_info", None)
        last_price = getattr(fast_info, "last_price", None) if fast_info is not None else None
        if last_price is not None:
            value = float(last_price)
            if value > 0:
                return value

        history = ticker.history(period="5d", interval="1d")
        if not history.empty:
            value = float(history.iloc[-1]["Close"])
            if value > 0:
                return value

        raise ValueError(f"No usable market price for {symbol}")

    return await asyncio.to_thread(_fetch)


@router.post("/forecast")
async def generate_forecast(payload: ForecastRequest, db: AsyncSession = Depends(get_db)):
    """Generate deterministic multi-model forecast outputs for requested horizons."""
    signal = intelligence_service.get_signal(payload.symbol)
    try:
        current_price = await _get_current_price(payload.symbol, db)
    except Exception:
        current_price = 1000.0
    model_results = []
    for model_name in ["tft", "hmm_garch", "gnn", "lstm_attn", "xgboost"]:
        forecasts = []
        base_signal = getattr(signal.models.get(model_name), "raw_signal", 0.0)
        for horizon in payload.horizons:
            directional_delta = base_signal * 0.004 * horizon
            low = current_price * (1 + directional_delta - 0.01)
            high = current_price * (1 + directional_delta + 0.01)
            forecasts.append(
                {
                    "target_date": datetime.now(UTC) + timedelta(days=horizon),
                    "horizon_days": horizon,
                    "predicted_price": round(current_price * (1 + directional_delta), 2),
                    "predicted_direction": signal.ensemble.direction,
                    "confidence": signal.ensemble.confidence,
                    "prediction_low": round(low, 2),
                    "prediction_high": round(high, 2),
                }
            )
        model_results.append({"model_name": model_name, "forecasts": forecasts})

    return {
        "symbol": payload.symbol.upper(),
        "current_price": current_price,
        "generated_at": datetime.now(UTC),
        "model_results": model_results,
    }


@router.get("/signals/{symbol}")
async def get_signals(symbol: str):
    """Get latest ensemble and model-level signal for a symbol."""
    return intelligence_service.get_signal(symbol)
