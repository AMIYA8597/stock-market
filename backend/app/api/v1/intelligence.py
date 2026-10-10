"""Advanced intelligence API routes for signals, regime, explainability, and monitoring."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.errors import ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)
from app.schemas.intelligence import (
    CorrelationGraphResponse,
    FactorExposureResponse,
    RegimeCurrentResponse,
    RegimeHistoryPoint,
    SignalHistoryPoint,
)
from app.services.intelligence_service import intelligence_service

router = APIRouter()

# Note: economic-calendar, regime/statistics, explain/*, and monitor/* used to
# be defined here too, duplicating market.py / regime.py / explain.py /
# models.py respectively. Because those dedicated routers are mounted first
# in api/v1/router.py, this router's copies were permanently unreachable
# dead code (FastAPI first-match routing). They were removed rather than
# fixed: those domains are each dedicated routers' responsibility (see the
# KT doc's "Where to Change What" table), and this router should not also
# silently own a second, divergent implementation of the same endpoints.


@router.get("/research/correlation-graph", response_model=CorrelationGraphResponse)
async def get_correlation_graph(
    window_days: int = Query(default=60, ge=30, le=252),
) -> CorrelationGraphResponse:
    """Return correlation graph nodes and edges for research workspace."""
    return await intelligence_service.get_correlation_graph(window_days=window_days)


@router.get("/research/factor-exposure", response_model=FactorExposureResponse)
async def get_factor_exposure(
    symbol: str = Query(default="RELIANCE.NS", min_length=2),
    window_days: int = Query(default=126, ge=63, le=504),
) -> FactorExposureResponse:
    """Return rolling factor exposures and diagnostics for selected symbol."""
    return await intelligence_service.get_factor_exposure(symbol=symbol, window_days=window_days)


@router.get("/signals/bulk")
async def get_bulk_signals(
    symbols: str = Query(..., description="Comma separated symbols, max 50"),
):
    """Return parallel signal snapshots for up to 50 symbols."""
    parsed = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="At least one symbol is required.",
            ).dict(),
        )
    if len(parsed) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse.create(
                code=ErrorCode.UNPROCESSABLE,
                message="A maximum of 50 symbols is allowed.",
            ).dict(),
        )
    return await intelligence_service.get_bulk_signals(parsed)


@router.get("/signals/{symbol}")
async def get_signal(symbol: str):
    """Return the latest ensemble and model-level signal for a symbol."""
    if len(symbol.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid symbol.",
            ).dict(),
        )
    try:
        return await intelligence_service.get_signal(symbol)
    except Exception as exc:
        logger.error("get_signal failed for %s: %s: %s", symbol, type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Signal computation temporarily unavailable.",
            ).dict(),
        ) from exc


@router.get("/signals/history/{symbol}", response_model=list[SignalHistoryPoint])
async def get_signal_history(
    symbol: str,
    model: str = Query(
        default="ensemble", pattern="^(ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost)$"
    ),
    days: int = Query(default=90, ge=30, le=252),
) -> list[SignalHistoryPoint]:
    """Return historical signal series and realized returns for model evaluation."""
    return await intelligence_service.get_signal_history(symbol=symbol.upper(), model=model, days=days)


@router.get("/regime/current", response_model=RegimeCurrentResponse)
async def get_regime_current() -> RegimeCurrentResponse:
    """Return current regime state, transition matrix, and conditional volatility."""
    return await intelligence_service.get_regime_current()


@router.get("/regime/history", response_model=list[RegimeHistoryPoint])
async def get_regime_history(
    days: int = Query(default=252, ge=30, le=504),
) -> list[RegimeHistoryPoint]:
    """Return daily regime labels and probabilities for the selected history window."""
    return await intelligence_service.get_regime_history(days)


