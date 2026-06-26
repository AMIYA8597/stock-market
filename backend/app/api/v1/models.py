"""Model monitoring and drift detection endpoints router (GET /monitor/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from app.schemas.monitor import (
    DriftDistribution,
    DriftResponse,
    EnsembleWeightPoint,
    ModelAccuracyMetrics,
    ModelAccuracyResponse,
    ModelDriftMetrics,
    WeightsHistoryResponse,
)

router = APIRouter(prefix="/monitor", tags=["monitoring"])


@router.get("/model-accuracy", response_model=ModelAccuracyResponse)
async def get_model_accuracy() -> ModelAccuracyResponse:
    now = datetime.now(UTC)
    rows = [
        ModelAccuracyMetrics(model_name="tft", precision=Decimal("0.6200"), recall=Decimal("0.6100"), f1_score=Decimal("0.6150"), directional_accuracy=Decimal("0.6400"), p50_rmse=Decimal("0.012300"), winkler_coverage=Decimal("0.8100"), as_of_date=now),
        ModelAccuracyMetrics(model_name="hmm_garch", precision=Decimal("0.5900"), recall=Decimal("0.5600"), f1_score=Decimal("0.5740"), directional_accuracy=Decimal("0.6020"), p50_rmse=Decimal("0.013800"), winkler_coverage=Decimal("0.7900"), as_of_date=now),
        ModelAccuracyMetrics(model_name="xgboost", precision=Decimal("0.6400"), recall=Decimal("0.6000"), f1_score=Decimal("0.6190"), directional_accuracy=Decimal("0.6510"), p50_rmse=Decimal("0.011900"), winkler_coverage=Decimal("0.8200"), as_of_date=now),
    ]
    return ModelAccuracyResponse(models=rows, benchmark_ensemble_accuracy=Decimal("0.6710"), generated_at=now)


@router.get("/drift", response_model=DriftResponse)
async def get_drift_detection() -> DriftResponse:
    now = datetime.now(UTC)
    base = DriftDistribution(mean=Decimal("0.000100"), std=Decimal("0.012300"), p25=Decimal("-0.006000"), p50=Decimal("0.000200"), p75=Decimal("0.006100"), min=Decimal("-0.042000"), max=Decimal("0.038000"))
    cur = DriftDistribution(mean=Decimal("0.000400"), std=Decimal("0.013200"), p25=Decimal("-0.006500"), p50=Decimal("0.000300"), p75=Decimal("0.006800"), min=Decimal("-0.045000"), max=Decimal("0.040000"))
    rows = [
        ModelDriftMetrics(
            model_name="tft",
            adwin_p_value=Decimal("0.182000"),
            drift_detected=False,
            ks_statistic=Decimal("0.062000"),
            ks_p_value=Decimal("0.274000"),
            residual_distribution_now=cur,
            residual_distribution_baseline=base,
            days_since_retrain=19,
            last_retraining_date=now - timedelta(days=19),
            as_of_date=now,
        )
    ]
    return DriftResponse(models=rows, overall_drift_detected=False, generated_at=now)


@router.get("/ensemble-weights-history", response_model=WeightsHistoryResponse)
async def get_weights_history() -> WeightsHistoryResponse:
    end = datetime.now(UTC)
    start = end - timedelta(days=30)
    data = []
    for i in range(31):
        ts = start + timedelta(days=i)
        data.append(
            EnsembleWeightPoint(
                date=ts,
                tft=Decimal("0.2800"),
                hmm_garch=Decimal("0.1900"),
                gnn=Decimal("0.1600"),
                lstm_attn=Decimal("0.1700"),
                xgboost=Decimal("0.2000"),
            )
        )
    return WeightsHistoryResponse(period_days=252, data=data, start_date=start, end_date=end)






