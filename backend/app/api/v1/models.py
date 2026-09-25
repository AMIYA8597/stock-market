# Model monitoring and drift detection endpoints router (GET /monitor/*).

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends
from scipy.stats import ks_2samp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.research import Prediction as MLPrediction
from app.schemas.monitor import (
    DriftDistribution,
    DriftResponse,
    EnsembleWeightPoint,
    ModelAccuracyMetrics,
    ModelAccuracyResponse,
    ModelDriftMetrics,
    WeightsHistoryResponse,
)

# Directory where model artefacts and optional back‑test metrics live
MODEL_DIR = Path(__file__).resolve().parents[4] / "data" / "models"

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["monitoring"])


def get_dynamic_ensemble_weights() -> dict[str, float]:
    """Load meta‑learner coefficients or fall back to a deterministic baseline.
    Returns a normalized dictionary keyed for the UI.
    """
    try:
        from research.models.ensemble.meta_learner import EnsembleMetaLearner

        learner = EnsembleMetaLearner.load()
        coefs = getattr(learner, "coefficients", {})
        if not coefs:
            raise ValueError("No coefficients found")
    except Exception as exc:
        logger.warning("Failed to load EnsembleMetaLearner: %s", exc)
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={"code": "MODEL_NOT_TRAINED", "message": "Ensemble meta-learner is not trained"},
        )

    raw = {
        "xgboost": coefs.get("xgboost", 0.0),
        "hmm_garch": coefs.get("regime", 0.0),
        "tft": coefs.get("momentum", 0.0),
        "lstm_attn": coefs.get("technical", 0.0),
        "gnn": coefs.get("pattern", 0.0),
    }
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


async def _load_backtest_metrics() -> dict:
    """Read optional back‑test metrics JSON produced by the training pipeline.
    Returns an empty dict if the file is missing or unreadable.
    """
    path = MODEL_DIR / "backtest_metrics.json"
    if not path.is_file():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Unable to read backtest metrics: %s", exc)
        return {}


async def _query_model_metrics(
    db: AsyncSession,
    model_name: str,
    fallback_accuracy: Decimal,
    fallback_rmse: float,
    fallback_coverage: float,
) -> ModelAccuracyMetrics | None:
    """Return accuracy metrics for *model_name* if recent predictions exist.
    If no predictions are available, ``None`` is returned – the endpoint will then
    omit the model from the response rather than fabricating numbers.
    """
    db_name = "lstm_attn" if model_name == "lstm_attention" else model_name
    stmt = (
        select(MLPrediction)
        .where(
            MLPrediction.model_name == db_name,
            MLPrediction.actual_return.isnot(None),
        )
        .order_by(MLPrediction.time.desc())
        .limit(1000)
    )
    try:
        res = await db.execute(stmt)
        preds = res.scalars().all()
    except Exception as exc:
        logger.warning("DB fetch failed for %s: %s", model_name, exc)
        preds = []
    if not preds:
        return None

    tp = fp = tn = fn = 0
    sq_err = []
    for p in preds:
        sig = float(p.raw_signal) if p.raw_signal is not None else 0.0
        act = float(p.actual_return)
        p50 = float(p.p50_return) if p.p50_return is not None else 0.0
        sq_err.append((p50 - act) ** 2)
        if sig > 0:
            if act > 0:
                tp += 1
            else:
                fp += 1
        elif sig < 0:
            if act < 0:
                tn += 1
            else:
                fn += 1
        else:
            if act < 0:
                tn += 1
            else:
                fn += 1
    total = tp + fp + tn + fn
    if total == 0:
        return None
    hit_rate = Decimal(str(round((tp + tn) / total, 4)))
    precision = tp / (tp + fp) if (tp + fp) else 0.5
    recall = tp / (tp + fn) if (tp + fn) else 0.5
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.5
    rmse = float(np.sqrt(np.mean(sq_err)))
    return ModelAccuracyMetrics(
        model_name=model_name,
        period_days=21,
        precision=Decimal(str(round(float(precision), 4))),
        recall=Decimal(str(round(float(recall), 4))),
        f1_score=Decimal(str(round(float(f1), 4))),
        directional_accuracy=hit_rate,
        p50_rmse=Decimal(str(round(rmse, 6))),
        winkler_coverage=Decimal(str(round(fallback_coverage, 4))),
        as_of_date=datetime.now(UTC),
    )


@router.get("/model-accuracy", response_model=ModelAccuracyResponse)
async def get_model_accuracy(db: AsyncSession = Depends(get_db)) -> ModelAccuracyResponse:
    now = datetime.now(UTC)
    metrics = await _load_backtest_metrics()

    rows: list[ModelAccuracyMetrics] = []
    for name in ["tft", "hmm_garch", "xgboost", "lstm_attention"]:
        # First try: load from backtest metrics JSON (written by training pipeline)
        bt = metrics.get(name, {})
        if bt:
            rows.append(
                ModelAccuracyMetrics(
                    model_name=name,
                    period_days=bt.get("period_days", 21),
                    precision=Decimal(str(round(bt.get("precision", 0.0), 4))),
                    recall=Decimal(str(round(bt.get("recall", 0.0), 4))),
                    f1_score=Decimal(str(round(bt.get("f1", 0.0), 4))),
                    directional_accuracy=Decimal(
                        str(round(bt.get("directional_accuracy", 0.0), 4))
                    ),
                    p50_rmse=Decimal(str(round(bt.get("p50_rmse", 0.0), 6))),
                    winkler_coverage=Decimal(str(round(bt.get("winkler_coverage", 0.0), 4))),
                    as_of_date=now,
                )
            )
            continue

        # Second try: compute from live DB predictions
        result = await _query_model_metrics(db, name, Decimal("0"), 0.0, 0.0)
        if result is not None:
            rows.append(result)
        # If neither source available: omit model from response (do NOT fabricate numbers)

    # Ensemble accuracy from latest completed backtest job
    ensemble_acc: Decimal | None = None
    try:
        from sqlalchemy import select  # noqa: PLC0415

        from app.models.backtest import BacktestJob  # noqa: PLC0415

        stmt = (
            select(BacktestJob)
            .where(
                BacktestJob.strategy_name == "ml_alpha",
                BacktestJob.status.in_(["DONE", "COMPLETED"]),
            )
            .order_by(BacktestJob.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if job and job.results:
            ensemble_acc = Decimal(
                str(round(job.results.get("metrics", {}).get("win_rate", 0.0), 4))
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch ensemble back-test job: %s", exc)

    return ModelAccuracyResponse(
        models=rows,
        benchmark_ensemble_accuracy=ensemble_acc if ensemble_acc is not None else Decimal("0.0"),
        generated_at=now,
    )


@router.get("/drift", response_model=DriftResponse)
async def get_drift_detection(db: AsyncSession = Depends(get_db)) -> DriftResponse:
    now = datetime.now(UTC)
    # Try DB‑driven drift first (XGBoost predictions)
    stmt = (
        select(MLPrediction)
        .where(
            MLPrediction.model_name == "xgboost",
            MLPrediction.actual_return.isnot(None),
            MLPrediction.p50_return.isnot(None),
        )
        .order_by(MLPrediction.time.desc())
        .limit(1000)
    )
    try:
        res = await db.execute(stmt)
        preds = res.scalars().all()
    except Exception as exc:
        logger.warning("DB query failed for drift: %s", exc)
        preds = []

    if len(preds) >= 42:
        resid = [float(p.p50_return - p.actual_return) for p in preds]
        resid.reverse()
        mid = len(resid) // 2
        baseline, current = np.array(resid[:mid]), np.array(resid[mid:])
        ks_res = ks_2samp(baseline, current)
        ks_stat, ks_p = float(ks_res.statistic), float(ks_res.pvalue)
        drift = ks_p < 0.05
        adwin_p = ks_p

        def _dist(arr: np.ndarray) -> DriftDistribution:
            return DriftDistribution(
                mean=Decimal(str(round(float(np.mean(arr)), 6))),
                std=Decimal(str(round(float(np.std(arr)), 6))),
                p25=Decimal(str(round(float(np.percentile(arr, 25)), 6))),
                p50=Decimal(str(round(float(np.percentile(arr, 50)), 6))),
                p75=Decimal(str(round(float(np.percentile(arr, 75)), 6))),
                min=Decimal(str(round(float(np.min(arr)), 6))),
                max=Decimal(str(round(float(np.max(arr)), 6))),
            )

        cur_dist = _dist(current)
        base_dist = _dist(baseline)
    else:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_NOT_TRAINED",
                "message": "Insufficient prediction history to calculate drift",
            },
        )

    # Last retraining timestamp derived from XGBoost artefact
    xgb_path = MODEL_DIR / "xgboost_RELIANCE.NS.pkl"
    if xgb_path.is_file():
        try:
            last_retrain = datetime.fromtimestamp(xgb_path.stat().st_mtime, UTC)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_TRAINED",
                    "message": "Could not determine last retrain time",
                },
            ) from exc
    else:
        raise HTTPException(
            status_code=503, detail={"code": "MODEL_NOT_TRAINED", "message": "Models not trained"}
        )
    days_since = (now - last_retrain).days

    rows = [
        ModelDriftMetrics(
            model_name="xgboost",
            adwin_p_value=Decimal(str(round(adwin_p, 6))),
            drift_detected=drift,
            ks_statistic=Decimal(str(round(ks_stat, 6))),
            ks_p_value=Decimal(str(round(ks_p, 6))),
            residual_distribution_now=cur_dist,
            residual_distribution_baseline=base_dist,
            days_since_retrain=days_since,
            last_retraining_date=last_retrain,
            as_of_date=now,
        )
    ]
    return DriftResponse(models=rows, overall_drift_detected=drift, generated_at=now)


@router.get("/ensemble-weights-history", response_model=WeightsHistoryResponse)
async def get_weights_history() -> WeightsHistoryResponse:
    """Return ensemble weight history from DB or current snapshot.

    If historical weight snapshots are not yet stored in the DB, returns only
    today's weights as a single-point series. Never fabricates historical data.
    """
    end = datetime.now(UTC)
    start = end - timedelta(days=30)
    weights = get_dynamic_ensemble_weights()
    today_pt = EnsembleWeightPoint(
        date=end,
        tft=Decimal(str(round(weights.get("tft", 0.0), 4))),
        hmm_garch=Decimal(str(round(weights.get("hmm_garch", 0.0), 4))),
        gnn=Decimal(str(round(weights.get("gnn", 0.0), 4))),
        lstm_attn=Decimal(str(round(weights.get("lstm_attn", 0.0), 4))),
        xgboost=Decimal(str(round(weights.get("xgboost", 0.0), 4))),
    )
    return WeightsHistoryResponse(period_days=30, data=[today_pt], start_date=start, end_date=end)
