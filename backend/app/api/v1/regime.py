"""Regime detection endpoints router (GET /regime/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.instrument import Instrument
from app.models.regime_states import RegimeState
from app.schemas.regime import (
    RegimeCurrentResponse,
    RegimeHistoryPoint,
    RegimeHistoryResponse,
    RegimeStatisticsResponse,
)

router = APIRouter(prefix="/regime", tags=["regime"])

LABELS = {0: "bull", 1: "bear", 2: "sideways"}


@router.get("/{symbol}/current", response_model=RegimeCurrentResponse)
async def get_regime_current(
    symbol: str, db: AsyncSession = Depends(get_db)
) -> RegimeCurrentResponse:
    try:
        clean_symbol = symbol.split(".")[0].upper()
        inst_res = await db.execute(
            select(Instrument).where(Instrument.canonical_symbol.startswith(clean_symbol))
        )
        instrument = inst_res.scalars().first()
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

        regime_res = await db.execute(
            select(RegimeState)
            .where(RegimeState.symbol_id == instrument.id)
            .order_by(RegimeState.time.desc())
            .limit(1)
        )
        regime = regime_res.scalars().first()

        if not regime:
            raise HTTPException(status_code=404, detail=f"No regime data computed yet for {symbol}")

        return RegimeCurrentResponse(
            state=LABELS.get(regime.viterbi_state, "bull"),
            state_index=regime.viterbi_state,
            probs=regime.state_probs,
            transition_matrix=None,
            cond_vol_1d=regime.conditional_vol,
            cond_vol_5d=regime.vol_forecast_5d or regime.conditional_vol,
            cond_vol_21d=regime.vol_forecast_21d or regime.conditional_vol,
            days_in_state=1,
            last_transition_date=regime.time,
            timestamp=regime.time,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Regime data unavailable: {e}") from e


@router.get("/{symbol}/history", response_model=RegimeHistoryResponse)
async def get_regime_history(
    symbol: str, days: int = Query(252, ge=1, le=1000), db: AsyncSession = Depends(get_db)
) -> RegimeHistoryResponse:
    try:
        clean_symbol = symbol.split(".")[0].upper()
        inst_res = await db.execute(
            select(Instrument).where(Instrument.canonical_symbol.startswith(clean_symbol))
        )
        instrument = inst_res.scalars().first()
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        regime_res = await db.execute(
            select(RegimeState)
            .where(RegimeState.symbol_id == instrument.id, RegimeState.time >= cutoff_date)
            .order_by(RegimeState.time.asc())
        )
        regimes = regime_res.scalars().all()

        points: list[RegimeHistoryPoint] = []
        transitions = 0
        last_state = None

        for r in regimes:
            if last_state is not None and r.viterbi_state != last_state:
                transitions += 1
            last_state = r.viterbi_state

            points.append(
                RegimeHistoryPoint(
                    time=r.time,
                    state=LABELS.get(r.viterbi_state, "bull"),
                    state_index=r.viterbi_state,
                    probs=r.state_probs,
                    cond_vol=r.conditional_vol,
                    cond_vol_5d=r.vol_forecast_5d or r.conditional_vol,
                    cond_vol_21d=r.vol_forecast_21d or r.conditional_vol,
                )
            )

        if not points:
            now = datetime.now(UTC)
            return RegimeHistoryResponse(
                period_days=days,
                start_date=now - timedelta(days=days),
                end_date=now,
                data=[],
                transitions=0,
            )

        return RegimeHistoryResponse(
            period_days=days,
            start_date=points[0].time,
            end_date=points[-1].time,
            data=points,
            transitions=transitions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Regime history unavailable: {e}") from e


@router.get("/statistics", response_model=RegimeStatisticsResponse)
async def get_regime_statistics() -> RegimeStatisticsResponse:
    # Not implementing actual global stats calculation for this test-mode since it requires heavy aggregation
    return RegimeStatisticsResponse(
        period_days=252,
        statistics=[],
        most_common_state="unknown",
        mean_duration_all_states=Decimal("0.0"),
    )
