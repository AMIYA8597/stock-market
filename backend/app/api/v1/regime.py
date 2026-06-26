"""Regime detection endpoints router (GET /regime/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Query
from app.schemas.regime import (
    RegimeCurrentResponse,
    RegimeHistoryPoint,
    RegimeHistoryResponse,
    RegimeStatistics,
    RegimeStatisticsResponse,
)

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/current", response_model=RegimeCurrentResponse)
async def get_regime_current() -> RegimeCurrentResponse:
    now = datetime.now(UTC)
    return RegimeCurrentResponse(
        state="bull",
        state_index=0,
        probs=[Decimal("0.6120"), Decimal("0.1320"), Decimal("0.2140"), Decimal("0.0420")],
        transition_matrix=[
            [Decimal("0.9120"), Decimal("0.0420"), Decimal("0.0360"), Decimal("0.0100")],
            [Decimal("0.1800"), Decimal("0.7240"), Decimal("0.0720"), Decimal("0.0240")],
            [Decimal("0.2100"), Decimal("0.1100"), Decimal("0.6400"), Decimal("0.0400")],
            [Decimal("0.0800"), Decimal("0.3900"), Decimal("0.1800"), Decimal("0.3500")],
        ],
        cond_vol_1d=Decimal("0.012300"),
        cond_vol_5d=Decimal("0.013100"),
        cond_vol_21d=Decimal("0.015400"),
        days_in_state=17,
        last_transition_date=now - timedelta(days=17),
        timestamp=now,
    )


@router.get("/history", response_model=RegimeHistoryResponse)
async def get_regime_history(
    days: int = Query(252, ge=1, le=1000),
) -> RegimeHistoryResponse:
    now = datetime.now(UTC)
    points: list[RegimeHistoryPoint] = []
    transitions = 0

    for i in range(min(days, 60)):
        t = now - timedelta(days=(min(days, 60) - i))
        idx = 0 if i < 20 else (2 if i < 40 else 1)
        if i in {20, 40}:
            transitions += 1
        label = ["bull", "bear", "sideways", "crisis"][idx]
        points.append(
            RegimeHistoryPoint(
                time=t,
                state=label,
                state_index=idx,
                probs=[Decimal("0.55"), Decimal("0.15"), Decimal("0.25"), Decimal("0.05")],
                cond_vol=Decimal("0.012300"),
                cond_vol_5d=Decimal("0.013100"),
                cond_vol_21d=Decimal("0.015400"),
            )
        )

    return RegimeHistoryResponse(
        period_days=days,
        start_date=points[0].time,
        end_date=points[-1].time,
        data=points,
        transitions=transitions,
    )


@router.get("/statistics", response_model=RegimeStatisticsResponse)
async def get_regime_statistics() -> RegimeStatisticsResponse:
    stats = [
        RegimeStatistics(
            state="bull",
            state_index=0,
            avg_duration_days=Decimal("18.40"),
            frequency_pct=Decimal("42.10"),
            avg_daily_return=Decimal("0.001120"),
            avg_volatility=Decimal("0.011200"),
            min_volatility=Decimal("0.007100"),
            max_volatility=Decimal("0.016500"),
            best_daily_return=Decimal("0.042100"),
            worst_daily_return=Decimal("-0.026700"),
        ),
        RegimeStatistics(
            state="bear",
            state_index=1,
            avg_duration_days=Decimal("11.25"),
            frequency_pct=Decimal("26.30"),
            avg_daily_return=Decimal("-0.000910"),
            avg_volatility=Decimal("0.018500"),
            min_volatility=Decimal("0.011100"),
            max_volatility=Decimal("0.032900"),
            best_daily_return=Decimal("0.028100"),
            worst_daily_return=Decimal("-0.051100"),
        ),
    ]
    return RegimeStatisticsResponse(
        period_days=252,
        statistics=stats,
        most_common_state="bull",
        mean_duration_all_states=Decimal("13.82"),
    )
