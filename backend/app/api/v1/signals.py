"""Signal prediction endpoints router (GET /signals/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.signal import (
    BulkSignalResponse,
    HistoricalSignal,
    SignalHistoryResponse,
    SignalResponse,
)

router = APIRouter(prefix="/signals", tags=["signals"])


def _build_signal(symbol: str) -> SignalResponse:
    now = datetime.now(UTC)
    return SignalResponse(
        symbol=symbol.upper(),
        timestamp=now,
        ensemble={
            "signal": Decimal("0.4200"),
            "confidence": Decimal("0.7310"),
            "direction": "BUY",
            "kelly_fraction": Decimal("0.0840"),
        },
        models={
            "tft": {"raw_signal": Decimal("0.3900"), "p10_return": Decimal("-0.011000"), "p50_return": Decimal("0.004200"), "p90_return": Decimal("0.016900")},
            "hmm_garch": {"regime_signal": Decimal("0.2800"), "vol_forecast_1d": Decimal("0.012300"), "vol_forecast_5d": Decimal("0.013100"), "vol_forecast_21d": Decimal("0.015400")},
            "gnn": {"spillover_risk": Decimal("0.2200"), "embedding_norm": Decimal("1.3120"), "top_correlated_assets": [{"ticker": "NIFTYBEES.NS", "correlation": 0.82}]},
            "lstm_attn": {"raw_signal": Decimal("0.4100"), "attention_peaks": [{"date": now.isoformat(), "weight": Decimal("0.0910")}]},
            "xgboost": {"raw_signal": Decimal("0.4700"), "top_features": [{"name": "momentum_21d", "shap_value": Decimal("0.0121")}]},
        },
        model_weights={
            "tft": Decimal("0.2800"),
            "hmm_garch": Decimal("0.1900"),
            "gnn": Decimal("0.1600"),
            "lstm_attn": Decimal("0.1700"),
            "xgboost": Decimal("0.2000"),
        },
        regime={"state": "bull", "probs": [0.61, 0.13, 0.21, 0.05], "transition_matrix": [[0.91, 0.04, 0.04, 0.01], [0.18, 0.72, 0.07, 0.03], [0.21, 0.11, 0.64, 0.04], [0.08, 0.39, 0.18, 0.35]]},
    )


@router.get("/bulk", response_model=BulkSignalResponse)
async def get_signals_bulk(
    symbols: str = Query(..., min_length=1, max_length=500),
    db: AsyncSession = Depends(get_db),
) -> BulkSignalResponse:
    _ = db
    parsed = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(parsed) == 0:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="At least one symbol is required.",
            ).dict(),
        )
    if len(parsed) > 50:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.UNPROCESSABLE,
                message="A maximum of 50 symbols is allowed.",
            ).dict(),
        )

    signals = [_build_signal(s) for s in parsed]
    return BulkSignalResponse(
        symbols=parsed,
        signals=signals,
        generated_at=datetime.now(UTC),
        total_symbols=len(parsed),
        processed_symbols=len(signals),
    )


@router.get("/history/{symbol}", response_model=SignalHistoryResponse)
async def get_signal_history(
    symbol: str,
    model: str = Query("ensemble", pattern="^(ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost)$"),
    days: int = Query(30, ge=1, le=252),
    db: AsyncSession = Depends(get_db),
) -> SignalHistoryResponse:
    _ = db
    now = datetime.now(UTC)

    rows = []
    for i in range(min(days, 90)):
        ts = now - timedelta(days=i)
        signal = Decimal("0.3000") if i % 3 != 0 else Decimal("-0.2200")
        direction = "BUY" if signal > 0 else "SELL"
        rows.append(
            HistoricalSignal(
                time=ts,
                signal=signal,
                confidence=Decimal("0.6700"),
                direction=direction,
                actual_return=Decimal("0.001200") if direction == "BUY" else Decimal("-0.000800"),
            )
        )

    return SignalHistoryResponse(
        symbol=symbol.upper(),
        model=model,
        period_days=days,
        data=rows,
        accuracy_metrics={"directional_accuracy": 0.61, "hit_rate": 0.58},
    )


@router.get("/{symbol}", response_model=SignalResponse)
async def get_signal(symbol: str, db: AsyncSession = Depends(get_db)) -> SignalResponse:
    _ = db
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )
    return _build_signal(symbol)
