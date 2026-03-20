"""ML prediction and signal API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from app.schemas.prediction import ForecastRequest
from app.services.intelligence_service import intelligence_service

router = APIRouter()


@router.post("/forecast")
async def generate_forecast(payload: ForecastRequest):
    """Generate deterministic multi-model forecast outputs for requested horizons."""
    signal = intelligence_service.get_signal(payload.symbol)
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
