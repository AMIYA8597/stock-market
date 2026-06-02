"""Prediction and ML signal schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    """Request to generate a price forecast."""
    symbol: str
    horizons: list[int] = Field(default=[1, 5, 30], description="Forecast horizons in days")
    models: list[str] | None = Field(
        default=None,
        description="Specific models to use. None = all available.",
    )


class ForecastPoint(BaseModel):
    """Single forecast data point."""
    target_date: datetime
    horizon_days: int
    predicted_price: float
    predicted_direction: str
    confidence: float
    prediction_low: float | None = None
    prediction_high: float | None = None


class ModelForecast(BaseModel):
    """Forecast results from a single model."""
    model_name: str
    forecasts: list[ForecastPoint]
    feature_importance: dict[str, float] | None = None
    attention_weights: list[float] | None = None


class ForecastResponse(BaseModel):
    """Complete forecast response with all model results."""
    symbol: str
    current_price: float
    generated_at: datetime
    model_results: list[ModelForecast]


class SignalResponse(BaseModel):
    """Trading signal for a symbol."""
    symbol: str
    strategy_name: str
    signal_type: str
    strength: float
    price_at_signal: float
    timestamp: datetime
