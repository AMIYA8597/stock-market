"""
Pydantic schemas for predictions endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionBase(BaseModel):
    """Base prediction schema."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    model_name: str = Field(..., description="ML model name")
    model_version: str = Field(..., description="Model version")
    horizon_days: int = Field(..., ge=1, le=365, description="Prediction horizon in days")


class PredictionResponse(PredictionBase):
    """Prediction response schema."""
    prediction_time: datetime
    predicted_price: Optional[float] = None
    predicted_direction: Optional[int] = Field(None, description="Predicted direction: +1 (up), -1 (down), 0 (neutral)")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Prediction confidence (0-1)")
    lower_80: Optional[float] = None
    upper_80: Optional[float] = None
    lower_95: Optional[float] = None
    upper_95: Optional[float] = None
    feature_importances: Optional[Dict[str, float]] = None
    actual_price: Optional[float] = None

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
    """Prediction request schema."""
    symbol: str = Field(..., min_length=1, max_length=20)
    horizon_days: int = Field(default=5, ge=1, le=30, description="Prediction horizon (1-30 days)")


class ModelInfoResponse(BaseModel):
    """Model information response."""
    name: str
    version: str
    description: str
    last_trained: datetime
    accuracy_metrics: Dict[str, float]
    feature_count: int
    supported_horizons: List[int]


class EnsemblePredictionResponse(BaseModel):
    """Ensemble prediction response with multiple models."""
    symbol: str
    horizon_days: int
    predictions: List[PredictionResponse]
    ensemble_prediction: PredictionResponse
    model_weights: Dict[str, float]
    disagreement_score: float  # 0-1, higher means more disagreement


class PredictionHistoryRequest(BaseModel):
    """Prediction history request."""
    symbol: str = Field(..., min_length=1, max_length=20)
    start_date: datetime
    end_date: datetime
    model_name: Optional[str] = None


class PredictionHistoryResponse(BaseModel):
    """Prediction history response."""
    symbol: str
    model_name: Optional[str]
    predictions: List[PredictionResponse]
    accuracy_stats: Dict[str, float]


class ModelPerformanceResponse(BaseModel):
    """Model performance metrics."""
    model_name: str
    version: str
    symbol: str
    horizon_days: int
    total_predictions: int
    directional_accuracy: float
    mean_absolute_error: float
    root_mean_squared_error: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float


class PredictionsResponse(BaseModel):
    """Generic predictions response."""
    success: bool
    message: str
    data: Optional[dict] = None