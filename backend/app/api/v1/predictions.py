"""
ML prediction API endpoints.

Implemented in Phase 3 with trained models.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.prediction import ForecastRequest

router = APIRouter()


@router.post("/forecast")
async def generate_forecast(payload: ForecastRequest):
    """Generate price forecast using ML models. (Phase 3)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ML engine not yet implemented — coming in Phase 3",
    )


@router.get("/signals/{symbol}")
async def get_signals(symbol: str):
    """Get latest trading signals for a symbol. (Phase 3)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Signal generator not yet implemented — coming in Phase 3",
    )
