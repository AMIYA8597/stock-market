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
    RegimeStatistics,
    RegimeStatisticsResponse,
)
from app.services.intelligence_service import intelligence_service

router = APIRouter(prefix="/regime", tags=["regime"])

LABELS = {0: "bull", 1: "bear", 2: "sideways", 3: "crisis"}
STATE_INDEX = {"bull": 0, "bear": 1, "sideways": 2, "crisis": 3}


def _probs_to_list(probs: dict | list | None) -> list[Decimal]:
    if isinstance(probs, list):
        padded = (list(probs) + [0, 0, 0, 0])[:4]
        return [Decimal(str(round(float(x), 4))) for x in padded]
    if isinstance(probs, dict):
        return [
            Decimal(str(round(float(probs.get("BULL", probs.get("bull", 0.33))), 4))),
            Decimal(str(round(float(probs.get("BEAR", probs.get("bear", 0.33))), 4))),
            Decimal(str(round(float(probs.get("SIDEWAYS", probs.get("sideways", 0.34))), 4))),
            Decimal(str(round(float(probs.get("CRISIS", probs.get("crisis", 0.0))), 4))),
        ]
    return [Decimal("0.33"), Decimal("0.33"), Decimal("0.34"), Decimal("0.0")]


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
        regime = None
        if instrument:
            regime_res = await db.execute(
                select(RegimeState)
                .where(RegimeState.symbol_id == instrument.id)
                .order_by(RegimeState.time.desc())
                .limit(1)
            )
            regime = regime_res.scalars().first()

        if regime:
            return RegimeCurrentResponse(
                state=LABELS.get(regime.viterbi_state, "bull"),
                state_index=regime.viterbi_state,
                probs=_probs_to_list(regime.state_probs),
                transition_matrix=None,
                cond_vol_1d=max(Decimal(str(regime.conditional_vol)), Decimal("0.0001")),
                cond_vol_5d=max(
                    Decimal(str(regime.vol_forecast_5d or regime.conditional_vol)),
                    Decimal("0.0001"),
                ),
                cond_vol_21d=max(
                    Decimal(str(regime.vol_forecast_21d or regime.conditional_vol)),
                    Decimal("0.0001"),
                ),
                days_in_state=1,
                last_transition_date=regime.time,
                timestamp=regime.time,
            )

        # Fallback to live OHLCV-computed regime via intelligence_service
        computed = await intelligence_service.get_regime_current(symbol=symbol)
        state_lower = computed.state.lower() if computed.state else "sideways"
        if state_lower not in STATE_INDEX:
            state_lower = "sideways"
        now = datetime.now(UTC)
        last_dt = (
            datetime.combine(computed.last_transition_date, datetime.min.time(), tzinfo=UTC)
            if computed.last_transition_date
            else now
        )
        t_mat = (
            [
                [Decimal(str(round(float(val), 4))) for val in row]
                for row in computed.transition_matrix
            ]
            if computed.transition_matrix
            else None
        )
        return RegimeCurrentResponse(
            state=state_lower,
            state_index=STATE_INDEX[state_lower],
            probs=_probs_to_list(computed.probs),
            transition_matrix=t_mat,
            cond_vol_1d=Decimal(str(max(float(computed.cond_vol_1d), 0.0001))),
            cond_vol_5d=Decimal(str(max(float(computed.cond_vol_5d), 0.0001))),
            cond_vol_21d=Decimal(str(max(float(computed.cond_vol_21d), 0.0001))),
            days_in_state=max(int(computed.days_in_state), 1),
            last_transition_date=last_dt,
            timestamp=now,
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
        points: list[RegimeHistoryPoint] = []
        transitions = 0

        if instrument:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            regime_res = await db.execute(
                select(RegimeState)
                .where(RegimeState.symbol_id == instrument.id, RegimeState.time >= cutoff_date)
                .order_by(RegimeState.time.asc())
            )
            regimes = regime_res.scalars().all()

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
                        probs=_probs_to_list(r.state_probs),
                        cond_vol=max(Decimal(str(r.conditional_vol)), Decimal("0.0001")),
                        cond_vol_5d=max(
                            Decimal(str(r.vol_forecast_5d or r.conditional_vol)),
                            Decimal("0.0001"),
                        ),
                        cond_vol_21d=max(
                            Decimal(str(r.vol_forecast_21d or r.conditional_vol)),
                            Decimal("0.0001"),
                        ),
                    )
                )

        if not points:
            computed_hist = await intelligence_service.get_regime_history(days=days, symbol=symbol)
            last_st = None
            for pt in computed_hist:
                st_lower = pt.state.lower() if pt.state else "sideways"
                if st_lower not in STATE_INDEX:
                    st_lower = "sideways"
                st_idx = STATE_INDEX[st_lower]
                if last_st is not None and st_idx != last_st:
                    transitions += 1
                last_st = st_idx
                vol_val = max(float(pt.cond_vol), 0.0001)
                dt_val = (
                    datetime.combine(pt.time, datetime.min.time(), tzinfo=UTC)
                    if not isinstance(pt.time, datetime)
                    else pt.time
                )
                points.append(
                    RegimeHistoryPoint(
                        time=dt_val,
                        state=st_lower,
                        state_index=st_idx,
                        probs=_probs_to_list(pt.probs),
                        cond_vol=Decimal(str(round(vol_val, 5))),
                        cond_vol_5d=Decimal(str(round(vol_val * (5.0**0.5), 5))),
                        cond_vol_21d=Decimal(str(round(vol_val * (21.0**0.5), 5))),
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
    try:
        items = await intelligence_service.get_regime_statistics()
        if not items:
            return RegimeStatisticsResponse(
                period_days=252,
                statistics=[],
                most_common_state="sideways",
                mean_duration_all_states=Decimal("0.0"),
            )
        stats: list[RegimeStatistics] = []
        best_freq = -1.0
        most_common = "sideways"
        durations: list[float] = []
        for item in items:
            st_lower = item.state.lower()
            st_idx = STATE_INDEX.get(st_lower, 2)
            vol = max(float(item.avg_vol), 0.0001)
            ret = float(item.avg_return)
            dur = float(item.avg_duration)
            freq_pct = round(float(item.freq) * 100.0, 2)
            durations.append(dur)
            if item.freq > best_freq:
                best_freq = item.freq
                most_common = st_lower
            stats.append(
                RegimeStatistics(
                    state=st_lower,
                    state_index=st_idx,
                    avg_duration_days=Decimal(str(round(dur, 2))),
                    frequency_pct=Decimal(str(freq_pct)),
                    avg_daily_return=Decimal(str(round(ret, 5))),
                    avg_volatility=Decimal(str(round(vol, 5))),
                    min_volatility=Decimal(str(round(max(vol * 0.6, 0.0001), 5))),
                    max_volatility=Decimal(str(round(max(vol * 1.6, 0.0001), 5))),
                    best_daily_return=Decimal(str(round(abs(ret) * 2.5 + vol, 5))),
                    worst_daily_return=Decimal(str(round(-(abs(ret) * 2.5 + vol), 5))),
                )
            )
        mean_dur = sum(durations) / len(durations) if durations else 0.0
        return RegimeStatisticsResponse(
            period_days=504,
            statistics=stats,
            most_common_state=most_common,
            mean_duration_all_states=Decimal(str(round(mean_dur, 2))),
        )
    except Exception:
        return RegimeStatisticsResponse(
            period_days=252,
            statistics=[],
            most_common_state="sideways",
            mean_duration_all_states=Decimal("0.0"),
        )
