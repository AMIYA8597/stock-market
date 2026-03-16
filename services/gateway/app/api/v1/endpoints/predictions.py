"""
ML predictions endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.predictions import (
    EnsemblePredictionResponse,
    ModelInfoResponse,
    ModelPerformanceResponse,
    PredictionHistoryResponse,
    PredictionRequest,
    PredictionResponse,
    PredictionsResponse,
)
from app.services.prediction_service import PredictionService

router = APIRouter()
prediction_service = PredictionService()


@router.post("/predict", response_model=PredictionResponse)
async def get_prediction(
    request: PredictionRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ML prediction for a symbol.
    """
    # Convert to service format
    service_request = {
        "symbol": request.symbol,
        "model_type": "amstan",  # Default model
        "prediction_horizon": request.horizon_days,
        "features": []
    }

    result = await prediction_service.get_prediction(service_request, db)

    return PredictionResponse(
        symbol=result.symbol,
        model_name=result.model_type,
        model_version=result.model_version,
        prediction_time=datetime.fromisoformat(result.prediction_date),
        horizon_days=request.horizon_days,
        predicted_price=result.predicted_price,
        predicted_direction=1 if result.predicted_price > 1000 else -1,  # TODO: Calculate properly
        confidence=result.confidence_score,
        lower_80=result.predicted_price * 0.95,  # TODO: Calculate properly
        upper_80=result.predicted_price * 1.05,
        lower_95=result.predicted_price * 0.90,
        upper_95=result.predicted_price * 1.10
    )


@router.post("/predict/ensemble", response_model=EnsemblePredictionResponse)
async def get_ensemble_prediction(
    request: PredictionRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ensemble prediction from multiple models.
    """
    result = await prediction_service.get_ensemble_prediction(request.symbol, request.horizon_days, db)

    return EnsemblePredictionResponse(
        symbol=request.symbol.upper(),
        horizon_days=request.horizon_days,
        predictions=[],  # TODO: Map individual predictions
        ensemble_prediction=PredictionResponse(
            symbol=request.symbol.upper(),
            model_name="ensemble",
            model_version="1.0.0",
            prediction_time=datetime.fromisoformat(result.prediction_date),
            horizon_days=request.horizon_days,
            predicted_price=result.ensemble_prediction,
            predicted_direction=1 if result.ensemble_prediction > 1000 else -1,
            confidence=result.ensemble_confidence
        ),
        model_weights={"AMSTAN": 0.6, "RL_Agent": 0.4},  # TODO: Get from result
        disagreement_score=0.1  # TODO: Calculate
    )


@router.get("/models", response_model=List[ModelInfoResponse])
async def list_models(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List available ML models.
    """
    models = await prediction_service.get_available_models(db)

    return [
        ModelInfoResponse(
            name=model.model_type,
            version=model.version,
            description=model.description,
            last_trained=datetime.fromisoformat(model.training_date),
            accuracy_metrics=model.accuracy_metrics,
            feature_count=len(model.features_used),
            supported_horizons=[1, 5, 10, 30]  # TODO: Get from model
        )
        for model in models
    ]


@router.get("/performance/{model_name}", response_model=ModelPerformanceResponse)
async def get_model_performance(
    model_name: str,
    symbol: str = Query(..., description="Stock symbol"),
    horizon_days: int = Query(..., description="Prediction horizon"),
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get model performance metrics.
    """
    result = await prediction_service.get_model_performance(model_name, symbol, db)

    return ModelPerformanceResponse(
        model_name=model_name,
        version="1.0.0",  # TODO: Get from result
        symbol=symbol.upper(),
        horizon_days=horizon_days,
        total_predictions=result.total_predictions,
        directional_accuracy=result.directional_accuracy,
        mean_absolute_error=result.mae,
        root_mean_squared_error=result.rmse,
        sharpe_ratio=result.sharpe_ratio or 0.0,
        max_drawdown=result.max_drawdown or 0.0,
        win_rate=0.65,  # TODO: Calculate
        profit_factor=result.profit_factor or 0.0
    )