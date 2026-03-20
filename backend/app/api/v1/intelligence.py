"""Advanced intelligence API routes for signals, regime, explainability, and monitoring."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.intelligence import (
    CorrelationGraphResponse,
    CounterfactualRequest,
    CounterfactualResponse,
    DriftItem,
    EconomicCalendarEvent,
    EnsembleWeightPoint,
    ExplainAttentionResponse,
    ExplainShapResponse,
    FactorExposureResponse,
    ModelAccuracyItem,
    RegimeCurrentResponse,
    RegimeHistoryPoint,
    RegimeStatisticsItem,
    SignalHistoryPoint,
    SignalResponse,
)
from app.services.intelligence_service import intelligence_service

router = APIRouter()


@router.get("/market/economic-calendar", response_model=List[EconomicCalendarEvent])
async def get_economic_calendar() -> List[EconomicCalendarEvent]:
    """Return upcoming high-impact macro and market events."""
    return intelligence_service.get_economic_calendar()


@router.get("/research/correlation-graph", response_model=CorrelationGraphResponse)
async def get_correlation_graph(window_days: int = Query(default=60, ge=30, le=252)) -> CorrelationGraphResponse:
    """Return correlation graph nodes and edges for research workspace."""
    return intelligence_service.get_correlation_graph(window_days=window_days)


@router.get("/research/factor-exposure", response_model=FactorExposureResponse)
async def get_factor_exposure(
    symbol: str = Query(default="RELIANCE.NS", min_length=2),
    window_days: int = Query(default=126, ge=63, le=504),
) -> FactorExposureResponse:
    """Return rolling factor exposures and diagnostics for selected symbol."""
    return intelligence_service.get_factor_exposure(symbol=symbol, window_days=window_days)


@router.get("/signals/{symbol}", response_model=SignalResponse)
async def get_signal(symbol: str) -> SignalResponse:
    """Return the latest ensemble and model-level signal for a symbol."""
    if len(symbol.strip()) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid symbol")
    return intelligence_service.get_signal(symbol)


@router.get("/signals/bulk", response_model=List[SignalResponse])
async def get_bulk_signals(symbols: str = Query(..., description="Comma separated symbols, max 50")) -> List[SignalResponse]:
    """Return parallel signal snapshots for up to 50 symbols."""
    parsed = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not parsed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No symbols provided")
    if len(parsed) > 50:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Maximum 50 symbols")
    return intelligence_service.get_bulk_signals(parsed)


@router.get("/signals/history/{symbol}", response_model=List[SignalHistoryPoint])
async def get_signal_history(
    symbol: str,
    model: str = Query(default="ensemble", pattern="^(ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost)$"),
    days: int = Query(default=90, ge=30, le=252),
) -> List[SignalHistoryPoint]:
    """Return historical signal series and realized returns for model evaluation."""
    return intelligence_service.get_signal_history(symbol=symbol.upper(), model=model, days=days)


@router.get("/regime/current", response_model=RegimeCurrentResponse)
async def get_regime_current() -> RegimeCurrentResponse:
    """Return current regime state, transition matrix, and conditional volatility."""
    return intelligence_service.get_regime_current()


@router.get("/regime/history", response_model=List[RegimeHistoryPoint])
async def get_regime_history(days: int = Query(default=252, ge=30, le=504)) -> List[RegimeHistoryPoint]:
    """Return daily regime labels and probabilities for the selected history window."""
    return intelligence_service.get_regime_history(days)


@router.get("/regime/statistics", response_model=List[RegimeStatisticsItem])
async def get_regime_statistics() -> List[RegimeStatisticsItem]:
    """Return aggregate per-regime summary statistics."""
    return intelligence_service.get_regime_statistics()


@router.get("/explain/shap/{symbol}", response_model=ExplainShapResponse)
async def get_shap_explainability(symbol: str) -> ExplainShapResponse:
    """Return SHAP feature attribution values for the latest inference."""
    return intelligence_service.get_shap(symbol)


@router.get("/explain/attention/{symbol}", response_model=ExplainAttentionResponse)
async def get_attention_explainability(
    symbol: str,
    model: str = Query(default="tft", pattern="^(tft|lstm_attn)$"),
) -> ExplainAttentionResponse:
    """Return temporal attention weights from the requested sequence model."""
    return intelligence_service.get_attention(symbol=symbol, model=model)


@router.post("/explain/counterfactual/{symbol}", response_model=List[CounterfactualResponse])
async def get_counterfactual(symbol: str, payload: CounterfactualRequest) -> List[CounterfactualResponse]:
    """Return counterfactual feature changes that can flip signal direction."""
    return intelligence_service.get_counterfactuals(symbol=symbol, payload=payload)


@router.get("/monitor/model-accuracy", response_model=List[ModelAccuracyItem])
async def get_model_accuracy() -> List[ModelAccuracyItem]:
    """Return rolling model quality metrics for each model family."""
    return intelligence_service.get_model_accuracy()


@router.get("/monitor/drift", response_model=List[DriftItem])
async def get_drift() -> List[DriftItem]:
    """Return concept drift diagnostics for production model monitoring."""
    return intelligence_service.get_drift()


@router.get("/monitor/ensemble-weights-history", response_model=List[EnsembleWeightPoint])
async def get_ensemble_weights_history(days: int = Query(default=252, ge=30, le=504)) -> List[EnsembleWeightPoint]:
    """Return historical dynamic ensemble weights for model governance analysis."""
    return intelligence_service.get_ensemble_weights_history(days)
