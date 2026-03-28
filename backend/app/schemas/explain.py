"""Explainability schemas — SHAP, attention, counterfactuals (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────━━
# SHAP Explainability
# ─────────────────────────────────────────────────────────────━━

class SHAPContribution(BaseModel):
    """Single feature's SHAP contribution."""
    name: str = Field(..., description="feature name")
    shap_value: Decimal = Field(..., decimal_places=6)
    feature_value: Decimal = Field(..., decimal_places=8)
    percentile_rank: Decimal = Field(..., ge=0.0, le=100.0, decimal_places=2)


class SHAPResponse(BaseModel):
    """GET /explain/shap/{symbol} response."""
    symbol: str
    model: str = Field(..., description="tft|lstm_attn|xgboost")
    feature_contributions: list[SHAPContribution]
    base_value: Decimal = Field(..., decimal_places=6, description="expected model output")
    output_value: Decimal = Field(..., decimal_places=6, description="actual prediction")
    waterfall_ready: bool = True
    timestamp: datetime


# ─────────────────────────────────────────────────────────────━━
# Attention Weights
# ─────────────────────────────────────────────────────────────━━

class AttentionTimestep(BaseModel):
    """Single important timestep."""
    date: datetime
    weight: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=6)


class AttentionResponse(BaseModel):
    """GET /explain/attention/{symbol} response."""
    symbol: str
    model: str = Field(..., description="tft|lstm_attn")
    weights: list[list[Decimal]] = Field(..., description="heads × timesteps matrix")
    mean_weights: list[Decimal] = Field(..., description="per-timestep avg weight")
    top_timesteps: list[AttentionTimestep] = Field(..., max_length=10)
    num_heads: int
    num_timesteps: int
    timestamp: datetime


# ─────────────────────────────────────────────────────────────━━
# Counterfactual Explanations
# ─────────────────────────────────────────────────────────────━━

class FeatureChange(BaseModel):
    """Feature value change in counterfactual."""
    name: str
    original_value: Decimal = Field(..., decimal_places=8)
    counterfactual_value: Decimal = Field(..., decimal_places=8)
    change_pct: Decimal = Field(..., decimal_places=2)


class CounterfactualInstance(BaseModel):
    """Single counterfactual explanation."""
    cf_id: str
    changed_features: list[FeatureChange]
    resulting_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    resulting_confidence: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4)
    proximity_score: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4, description="distance to original")


class CounterfactualRequest(BaseModel):
    """POST /explain/counterfactual/{symbol} request body."""
    target_direction: str = Field(..., description="BUY|SELL")
    num_cfs: int = Field(default=5, ge=1, le=20)


class CounterfactualResponse(BaseModel):
    """POST /explain/counterfactual/{symbol} response."""
    symbol: str
    target_direction: str
    counterfactuals: list[CounterfactualInstance]
    original_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    original_confidence: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4)
    timestamp: datetime
