# backend/app/api/v1/predictions.py
"""Predictions endpoint
Returns AI model predictions for a single symbol.
Provides forecast trajectories, support/resistance levels, and signals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_rate_limiter
from app.database.connection import get_db
from app.models.instrument import Instrument
from app.models.model_artifact import ModelArtifact
from app.schemas.errors import ErrorResponse
from app.schemas.prediction import ForecastRequest
from app.services.market_data_service import MarketDataService
from app.services.prediction_engine import get_full_prediction

router = APIRouter()


@router.get("/{symbol}")
async def get_prediction(
    symbol: str, 
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    norm_symbol = MarketDataService._normalize_symbol(symbol)

    # Check if we have an active XGBoost model for this symbol
    stmt = (
        select(ModelArtifact)
        .join(Instrument)
        .where(
            Instrument.symbol == norm_symbol,
            ModelArtifact.is_active,
        )
    )
    result = await db.execute(stmt)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code="MODEL_NOT_TRAINED",
                message=f"ML prediction engine is offline until training phase for {symbol}."
            ).dict()
        )

    return await get_full_prediction(
        symbol,
        bypass_cache=False,
        artifact_path=artifact.artifact_path,
        model_version=artifact.version_tag
    )

@router.post("/forecast")
async def generate_forecast(
    payload: ForecastRequest,
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    raise HTTPException(
        status_code=503,
        detail=ErrorResponse.create(
            code="MODEL_NOT_TRAINED",
            message="ML prediction engine is offline until training phase."
        ).dict()
    )

@router.get("/latest/{symbol}")
async def get_latest_forecast(
    symbol: str, 
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    return await get_prediction(symbol, db)

@router.get("/ensemble/{symbol}")
async def get_ensemble_data(
    symbol: str,
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    raise HTTPException(
        status_code=503,
        detail=ErrorResponse.create(
            code="MODEL_NOT_TRAINED",
            message="ML prediction engine is offline until training phase."
        ).dict()
    )

@router.get("/history/{symbol}")
async def get_prediction_history(symbol: str, db: AsyncSession = Depends(get_db)):
    from app.models.model_metric import ModelMetric

    norm_symbol = MarketDataService._normalize_symbol(symbol)

    stmt = (
        select(ModelMetric, ModelArtifact)
        .join(ModelArtifact, ModelMetric.artifact_id == ModelArtifact.id)
        .join(Instrument, ModelArtifact.symbol_id == Instrument.id)
        .where(
            Instrument.symbol == norm_symbol,
            ModelArtifact.is_active,
        )
        .order_by(ModelMetric.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code="MODEL_NOT_TRAINED",
                message="No metrics available."
            ).dict()
        )

    metric, artifact = row

    return {
        "accuracy_metrics": {
            "accuracy": metric.accuracy,
            "precision": metric.precision,
            "recall": metric.recall,
            "sharpe": metric.sharpe,
            "cost_adjusted_sharpe": metric.cost_adjusted_sharpe,
            "recent_trades": [], # Cannot invent this per honesty law
            "regime_breakdown": metric.regime_breakdown
        }
    }

