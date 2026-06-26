# backend/app/api/v1/predictions.py
"""Predictions endpoint – provides SARIMAX based forecasts.

Replaces the fake linear forecast with real model output.
"""

from __future__ import annotations
import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.schemas.prediction import ForecastRequest
from app.services.prediction_engine import get_full_prediction

router = APIRouter()

@router.post("/forecast")
async def generate_forecast(payload: ForecastRequest):
    try:
        result = await get_full_prediction(payload.symbol)
        return {
            "symbol": payload.symbol.upper(),
            "current_price": result["current_price"],
            "generated_at": datetime.now(UTC),
            "forecast": result["forecast"],
            "ensemble_direction": result["ensemble"]["direction"],
            "confidence": result["ensemble"]["confidence"],
            "data_points_used": result["data_points_used"]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/latest/{symbol}")
async def get_latest_forecast(symbol: str):
    """Return the forecast entry for horizon_days == 5."""
    try:
        result = await get_full_prediction(symbol)
        forecast = result.get("forecast", [])
        # Find where horizon_days equals 5
        pt5 = next((pt for pt in forecast if pt["horizon_days"] == 5), None)
        if pt5 is None:
            if forecast:
                pt5 = forecast[0]
            else:
                raise ValueError("No forecast available")
        return pt5
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/ensemble/{symbol}")
async def get_ensemble_data(symbol: str):
    """Return the model weights and sub-model scores."""
    try:
        result = await get_full_prediction(symbol)
        ensemble = result["ensemble"]
        return {
            "symbol": symbol.upper(),
            "model_weights": ensemble.get("model_weights", {}),
            "scores": {
                "technical": ensemble.get("technical", {}).get("score", 0.0),
                "pattern": ensemble.get("pattern", {}).get("pattern_score", 0.0),
                "momentum": ensemble.get("momentum", {}).get("momentum_score", 0.0),
                "regime": ensemble.get("regime", {}).get("regime_confidence", 0.0) if ensemble.get("regime", {}).get("regime") == "BULL" else -ensemble.get("regime", {}).get("regime_confidence", 0.0) if ensemble.get("regime", {}).get("regime") == "BEAR" else 0.0,
                "xgboost": ensemble.get("xgboost", {}).get("xgb_score", 0.0),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
