"""Pydantic schemas for ML Inference Orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SignalPrediction(BaseModel):
    """Single model prediction."""

    model_name: str
    p50_return: float = Field(..., description="Median predicted return")
    p10_return: Optional[float] = Field(None, description="10th percentile")
    p90_return: Optional[float] = Field(None, description="90th percentile")
    raw_signal: float = Field(..., description="Continuous signal in [-1, +1]")
    confidence: float = Field(..., description="Model confidence in [0, 1]")
    horizon_days: int = Field(default=1)
    shap_values: Optional[dict[str, float]] = None
    attention_weights: Optional[dict[str, float]] = None


class RegimeState(BaseModel):
    """HMM regime state information."""

    state: int = Field(..., description="0=bull, 1=bear, 2=sideways, 3=crisis")
    probs: list[float] = Field(..., description="[P(bull), P(bear), P(side), P(crisis)]")
    conditional_vol: float = Field(..., description="1-day conditional volatility")
    vol_forecast_5d: float = Field(..., description="5-day vol forecast")
    vol_forecast_21d: float = Field(..., description="21-day vol forecast")


class EnsembleSignal(BaseModel):
    """Final aggregated ensemble signal."""

    symbol: str
    timestamp: datetime
    signal: float = Field(..., description="Final signal in [-1, +1]")
    confidence: float = Field(..., description="Ensemble agreement in [0, 1]")
    direction: str = Field(..., description="STRONG_BUY|BUY|NEUTRAL|SELL|STRONG_SELL")
    kelly_fraction: float = Field(..., description="Position sizing from Kelly")
    model_weights: dict[str, float] = Field(..., description="Per-model weights")
    regime_state: RegimeState = Field(...)
    individual_signals: dict[str, SignalPrediction] = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)
