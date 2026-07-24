"""Model monitoring and drift detection schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ModelAccuracyMetrics(BaseModel):
    """Rolling accuracy metrics for single model."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    period_days: int = 21
    precision: Decimal = Field(..., ge=0, le=1)
    recall: Decimal = Field(..., ge=0, le=1)
    f1_score: Decimal = Field(..., ge=0, le=1)
    directional_accuracy: Decimal = Field(..., ge=0, le=1)
    p50_rmse: Decimal = Field(..., ge=0)
    winkler_coverage: Decimal = Field(..., ge=0, le=1)
    as_of_date: datetime


class ModelAccuracyResponse(BaseModel):
    """GET /monitor/model-accuracy response."""

    models: list[ModelAccuracyMetrics]
    benchmark_ensemble_accuracy: Decimal = Field(..., ge=0, le=1)
    generated_at: datetime


class DriftDistribution(BaseModel):
    """Residual distribution statistics."""

    mean: Decimal = Field(...)
    std: Decimal = Field(..., ge=0)
    p25: Decimal = Field(...)
    p50: Decimal = Field(...)
    p75: Decimal = Field(...)
    min: Decimal = Field(...)
    max: Decimal = Field(...)


class ModelDriftMetrics(BaseModel):
    """Drift detection for single model."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    adwin_p_value: Decimal = Field(..., ge=0, le=1)
    drift_detected: bool
    ks_statistic: Decimal = Field(..., ge=0, le=1)
    ks_p_value: Decimal = Field(..., ge=0, le=1)
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
    tft: Decimal = Field(..., ge=0, le=1)
    hmm_garch: Decimal = Field(..., ge=0, le=1)
    gnn: Decimal = Field(..., ge=0, le=1)
    lstm_attn: Decimal = Field(..., ge=0, le=1)
    xgboost: Decimal = Field(..., ge=0, le=1)


class WeightsHistoryResponse(BaseModel):
    """GET /monitor/ensemble-weights-history response."""

    period_days: int = 252
    data: list[EnsembleWeightPoint]
    start_date: datetime
    end_date: datetime
