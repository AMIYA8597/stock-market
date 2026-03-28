"""Model monitoring and drift detection schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelAccuracyMetrics(BaseModel):
    """Rolling accuracy metrics for single model."""
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    period_days: int = 21
    precision: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    recall: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    f1_score: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    directional_accuracy: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    p50_rmse: Decimal = Field(..., ge=0, decimal_places=6)
    winkler_coverage: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    as_of_date: datetime


class ModelAccuracyResponse(BaseModel):
    """GET /monitor/model-accuracy response."""
    models: list[ModelAccuracyMetrics]
    benchmark_ensemble_accuracy: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    generated_at: datetime


class DriftDistribution(BaseModel):
    """Residual distribution statistics."""
    mean: Decimal = Field(..., decimal_places=6)
    std: Decimal = Field(..., ge=0, decimal_places=6)
    p25: Decimal = Field(..., decimal_places=6)
    p50: Decimal = Field(..., decimal_places=6)
    p75: Decimal = Field(..., decimal_places=6)
    min: Decimal = Field(..., decimal_places=6)
    max: Decimal = Field(..., decimal_places=6)


class ModelDriftMetrics(BaseModel):
    """Drift detection for single model."""
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    adwin_p_value: Decimal = Field(..., ge=0, le=1, decimal_places=6)
    drift_detected: bool
    ks_statistic: Decimal = Field(..., ge=0, le=1, decimal_places=6)
    ks_p_value: Decimal = Field(..., ge=0, le=1, decimal_places=6)
    residual_distribution_now: DriftDistribution
    residual_distribution_baseline: DriftDistribution
    days_since_retrain: int
    last_retraining_date: datetime
    as_of_date: datetime


class DriftResponse(BaseModel):
    """GET /monitor/drift response."""
    models: list[ModelDriftMetrics]
    overall_drift_detected: bool
    generated_at: datetime


class EnsembleWeightPoint(BaseModel):
    """Single point in ensemble weights history."""
    date: datetime
    tft: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    hmm_garch: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    gnn: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    lstm_attn: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    xgboost: Decimal = Field(..., ge=0, le=1, decimal_places=4)


class WeightsHistoryResponse(BaseModel):
    """GET /monitor/ensemble-weights-history response."""
    period_days: int = 252
    data: list[EnsembleWeightPoint]
    start_date: datetime
    end_date: datetime
