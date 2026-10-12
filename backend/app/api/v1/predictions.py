# backend/app/api/v1/predictions.py
"""Predictions endpoint
Returns AI model predictions for a single symbol.
Provides forecast trajectories, support/resistance levels, and signals.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_rate_limiter
from app.database.connection import get_db
from app.models.instrument import Instrument
from app.models.model_artifact import ModelArtifact
from app.models.model_metric import ModelMetric
from app.schemas.errors import ErrorResponse
from app.schemas.prediction import ForecastRequest
from app.services.market_data_service import MarketDataService
from app.services.prediction_engine import forecast_multi_horizon, get_full_prediction

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum time to wait for the heavy prediction pipeline before returning fallback
_PREDICTION_TIMEOUT_SECONDS = 8


def _fallback_prediction(symbol: str) -> dict:
    """Return a lightweight fallback prediction when the full pipeline is too slow or fails."""
    from datetime import UTC, datetime

    return {
        "symbol": symbol,
        "is_fallback": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "ensemble": {
            "direction": "NEUTRAL",
            "confidence": 0.5,
            "signal": "NEUTRAL",
            "model_weights": {},
        },
        "regime": {
            "current_state": "unknown",
            "probs": {"bull": 0.25, "bear": 0.25, "sideways": 0.25, "crisis": 0.25},
        },
        "forecast": [],
        "models": {},
        "reasoning": "Signal computation in progress — data will appear shortly.",
    }


@router.get("/{symbol}")
async def get_prediction(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60)),
):
    norm_symbol = MarketDataService._normalize_symbol(symbol)

    # Fast path: check cache directly first (avoids DB + heavy pipeline)
    from app.services.prediction_engine import _cache_fetch

    cached = await _cache_fetch(norm_symbol)
    if cached:
        return cached

    # Check if we have an active XGBoost model for this symbol
    artifact_path = None
    model_version = None
    try:
        stmt = (
            select(ModelArtifact)
            .join(Instrument)
            .where(
                Instrument.canonical_symbol == norm_symbol,
                ModelArtifact.is_active,
            )
        )
        result = await db.execute(stmt)
        artifact = result.scalar_one_or_none()
        if artifact:
            artifact_path = artifact.artifact_path
            model_version = artifact.version_tag
    except Exception:
        pass

    # Run prediction with a timeout — return fallback if it takes too long
    try:
        return await asyncio.wait_for(
            get_full_prediction(
                symbol,
                bypass_cache=False,
                artifact_path=artifact_path,
                model_version=model_version,
            ),
            timeout=_PREDICTION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning("Prediction for %s timed out after %ss, returning fallback", norm_symbol, _PREDICTION_TIMEOUT_SECONDS)
        return _fallback_prediction(norm_symbol)
    except Exception as e:
        logger.warning("Prediction failed for %s: %s, returning fallback", norm_symbol, e)
        return _fallback_prediction(norm_symbol)


@router.post("/forecast")
async def generate_forecast(
    payload: ForecastRequest, _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    """Multi-horizon SARIMAX price forecast — real statistical forecasting on
    real OHLCV history, not a stub. Each horizon reports the actual data
    window it was fit on and an honest confidence label; horizons under 1h
    are only ever backed by ~60 days of intraday data (a free-data-source
    limit, not a modeling choice) and are labeled accordingly.
    """
    norm_symbol = MarketDataService._normalize_symbol(payload.symbol)
    result = await forecast_multi_horizon(norm_symbol, payload.horizons)
    return result


@router.get("/latest/{symbol}")
async def get_latest_forecast(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60)),
):
    return await get_prediction(symbol, db)


@router.get("/ensemble/{symbol}")
async def get_ensemble_data(
    symbol: str, _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    norm_symbol = MarketDataService._normalize_symbol(symbol)
    try:
        result = await get_full_prediction(norm_symbol, bypass_cache=False)
        ens = result.get("ensemble", {})
        models = []
        model_weights = ens.get("model_weights", {})
        for name, weight in model_weights.items():
            models.append({"name": name, "weight": float(weight)})
        return {
            "symbol": norm_symbol,
            "consensus_direction": ens.get("direction", "NEUTRAL"),
            "consensus_confidence": float(ens.get("confidence", 0.5)),
            "models": models,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code="MODEL_NOT_TRAINED",
                message=f"Ensemble unavailable for {symbol}: {str(e)[:200]}",
            ).dict(),
        )


@router.get("/history/{symbol}")
async def get_prediction_history(symbol: str, db: AsyncSession = Depends(get_db)):
    norm_symbol = MarketDataService._normalize_symbol(symbol)

    stmt = (
        select(ModelMetric, ModelArtifact)
        .join(ModelArtifact, ModelMetric.artifact_id == ModelArtifact.id)
        .join(Instrument, ModelArtifact.symbol_id == Instrument.id)
        .where(
            Instrument.canonical_symbol == norm_symbol,
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
                code="MODEL_NOT_TRAINED", message="No metrics available."
            ).dict(),
        )

    metric, artifact = row

    return {
        "accuracy_metrics": {
            "accuracy": metric.accuracy,
            "precision": metric.precision,
            "recall": metric.recall,
            "sharpe": metric.sharpe,
            "cost_adjusted_sharpe": metric.cost_adjusted_sharpe,
            "recent_trades": [],  # Cannot invent this per honesty law
            "regime_breakdown": metric.regime_breakdown,
        }
    }


@router.get("/mtf/{symbol}")
async def get_mtf_prediction_endpoint(
    symbol: str,
    timeframes: str | None = None,
    _rate_limit: None = Depends(get_rate_limiter(requests=5, window=60)),
):
    """Multi-timeframe prediction across 1m to 1D.

    Combines candlestick pattern recognition, technical indicator signals,
    and trend classification across all requested timeframes.

    Query param ``timeframes``: comma-separated list (e.g. "5m,15m,1h,1D").
    Omit for all timeframes.

    NOTE: Predictions use rule-based heuristics.  The ``data_source`` field
    in each response object indicates this.  ML-model-backed predictions
    will be enabled after model training (Phase 7).
    """
    from app.services.mtf_prediction import Timeframe, get_mtf_prediction

    norm_symbol = MarketDataService._normalize_symbol(symbol)

    tf_list = None
    if timeframes:
        tf_list = [t.strip() for t in timeframes.split(",")]
        valid = {tf.value for tf in Timeframe}
        invalid = [t for t in tf_list if t not in valid]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframes: {invalid}. Valid: {sorted(valid)}",
            )

    try:
        result = await get_mtf_prediction(norm_symbol, tf_list)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code="MTF_PREDICTION_FAILED",
                message=f"Multi-timeframe prediction unavailable for {symbol}: {str(e)[:200]}",
            ).dict(),
        )


@router.get("/model-inventory")
async def model_inventory():
    """Return honest inventory of all ML models and their training status."""
    from pathlib import Path

    MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models"
    ARTIFACT_DIR = Path(__file__).parent.parent.parent / "data" / "artifacts"

    models = {
        "xgboost": {
            "name": "XGBoost Directional Classifier",
            "type": "gradient_boosting",
            "status": "untrained",
            "artifact_pattern": "xgboost_*.pkl",
            "description": "Real XGBClassifier with isotonic calibration and SHAP explainability",
        },
        "lstm_attention": {
            "name": "LSTM-Attention Classifier",
            "type": "deep_learning",
            "status": "untrained",
            "artifact_pattern": "lstm_attention_*.pkl",
            "description": "PyTorch LSTM with learned attention weights (32 hidden, 20 epochs)",
        },
        "hmm_garch": {
            "name": "HMM-GARCH Regime Detector",
            "type": "statistical",
            "status": "trained",
            "description": "From-scratch Student-t HMM + GARCH(1,1). Fits on-the-fly from price data.",
        },
        "tft_quantile": {
            "name": "Quantile LightGBM Forecaster",
            "actual_model": "LightGBM (NOT Temporal Fusion Transformer)",
            "type": "gradient_boosting",
            "status": "untrained",
            "artifact_pattern": "tft_forecaster.pkl",
            "description": "3 quantile LightGBM regressors (p10/p50/p90). Labeled 'TFT' in legacy code but is LightGBM.",
        },
        "gnn_contagion": {
            "name": "Contagion Risk Analyzer",
            "actual_model": "Formula-based heuristic (NOT a trained GNN)",
            "type": "heuristic",
            "status": "heuristic",
            "description": "Computes correlation-based contagion risk. Real GNN architecture exists in research/models/gnn/model.py but is not used in production.",
        },
        "online_learner": {
            "name": "Online Adaptive Learner",
            "type": "online_learning",
            "status": "untrained",
            "artifact_pattern": "online_learner_*.pkl",
            "description": "Incremental logistic regression updated with each prediction call.",
        },
        "lstm_forecaster": {
            "name": "LSTM Price Forecaster",
            "type": "deep_learning",
            "status": "trains_from_scratch",
            "description": "Trains a fresh LSTM/BiLSTM/GRU/CNN-LSTM for 15 epochs per call. Not a pre-trained model.",
        },
        "meta_learner": {
            "name": "Ensemble Meta-Learner",
            "type": "ensemble",
            "status": "untrained",
            "artifact_pattern": "meta_learner.pkl",
            "description": "Logistic regression combining OOF predictions from all component models.",
        },
        "finbert_sentiment": {
            "name": "FinBERT Sentiment Analyzer",
            "type": "nlp",
            "status": "pretrained",
            "description": "ProsusAI/finbert for financial sentiment. Falls back to VADER if transformers unavailable.",
        },
    }

    for _key, model in models.items():
        pattern = model.get("artifact_pattern")
        if pattern:
            found = list(MODEL_DIR.glob(pattern)) + list(ARTIFACT_DIR.glob(pattern))
            if found:
                model["status"] = "trained"
                model["artifact_paths"] = [str(f.name) for f in found]

    hmm_json = list(MODEL_DIR.glob("hmm_garch/*.json"))
    if hmm_json:
        models["hmm_garch"]["artifact_paths"] = [str(f.name) for f in hmm_json]

    trained = sum(1 for m in models.values() if m["status"] == "trained")
    total = len(models)

    return {
        "models": models,
        "summary": {
            "total": total,
            "trained": trained,
            "untrained": total - trained,
            "production_ready": trained >= 3,
        },
    }
