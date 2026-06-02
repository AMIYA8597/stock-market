"""Backtest execution endpoints router (POST/GET /backtest/*)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRequest,
    BacktestResultsResponse,
    BacktestRunResponse,
    BacktestStatusResponse,
    DrawdownPoint,
    EquityCurvePoint,
    StatisticalTests,
    TradeLogEntry,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunResponse, status_code=202)
async def post_backtest_run(request: BacktestRequest, db: AsyncSession = Depends(get_db)) -> BacktestRunResponse:
    _ = db
    days = max((request.date_to - request.date_from).days, 1)
    estimate = min(3600, 30 + len(request.universe) * days // 20)
    return BacktestRunResponse(
        job_id=str(uuid4()),
        status="PENDING",
        estimated_seconds=estimate,
        universe_size=len(request.universe),
        period_days=days,
    )


@router.get("/status/{job_id}", response_model=BacktestStatusResponse)
async def get_backtest_status(job_id: str, db: AsyncSession = Depends(get_db)) -> BacktestStatusResponse:
    _ = db
    return BacktestStatusResponse(
        job_id=job_id,
        status="RUNNING",
        progress_pct=67,
        current_date=date.today() - timedelta(days=12),
        equity_value=Decimal("1123456.78"),
        estimated_remaining_seconds=95,
        error_message=None,
    )


@router.get("/results/{job_id}", response_model=BacktestResultsResponse)
async def get_backtest_results(job_id: str, db: AsyncSession = Depends(get_db)) -> BacktestResultsResponse:
    _ = db
    start = date.today() - timedelta(days=30)

    equity = [
        EquityCurvePoint(
            date=start + timedelta(days=i),
            portfolio_value=Decimal("1000000.00") + Decimal(i * 4200),
            benchmark_value=Decimal("1000000.00") + Decimal(i * 3100),
        )
        for i in range(30)
    ]
    drawdown = [
        DrawdownPoint(date=start + timedelta(days=i), drawdown_pct=Decimal("0.0000") if i < 10 else Decimal("0.0180"))
        for i in range(30)
    ]
    trades = [
        TradeLogEntry(
            date=start + timedelta(days=2),
            symbol="RELIANCE.NS",
            direction="BUY",
            quantity=Decimal("10.00000000"),
            price=Decimal("2480.12000000"),
            pnl=Decimal("0.00"),
            cum_pnl=Decimal("0.00"),
            commission=Decimal("14.20"),
        ),
        TradeLogEntry(
            date=start + timedelta(days=11),
            symbol="RELIANCE.NS",
            direction="SELL",
            quantity=Decimal("10.00000000"),
            price=Decimal("2552.44000000"),
            pnl=Decimal("723.20"),
            cum_pnl=Decimal("723.20"),
            commission=Decimal("14.20"),
        ),
    ]

    metrics = BacktestMetrics(
        total_return=Decimal("0.1260"),
        cagr=Decimal("0.1890"),
        sharpe_ratio=Decimal("1.3100"),
        sortino_ratio=Decimal("1.9200"),
        calmar_ratio=Decimal("1.2400"),
        omega_ratio=Decimal("1.1600"),
        max_drawdown=Decimal("0.1010"),
        max_drawdown_duration_days=12,
        win_rate=Decimal("0.5800"),
        profit_factor=Decimal("1.4200"),
        avg_win=Decimal("910.20"),
        avg_loss=Decimal("-541.10"),
        payoff_ratio=Decimal("1.6800"),
        num_trades=42,
        gross_profit=Decimal("18204.00"),
        gross_loss=Decimal("-12810.20"),
        tail_ratio=Decimal("1.0900"),
        serenity_ratio=Decimal("0.8800"),
        deflated_sharpe=Decimal("0.7300"),
    )

    return BacktestResultsResponse(
        job_id=job_id,
        strategy_name="ensemble",
        universe=["RELIANCE.NS", "TCS.NS", "INFY.NS"],
        date_from=start,
        date_to=date.today(),
        initial_capital=Decimal("1000000.00"),
        metrics=metrics,
        equity_curve=equity,
        drawdown_series=drawdown,
        trade_log=trades,
        walk_forward=None,
        monte_carlo=None,
        statistical_tests=StatisticalTests(
            dm_test_statistic=Decimal("-1.920000"),
            dm_test_p_value=Decimal("0.054200"),
            dm_test_vs_benchmark="ARIMA",
            sharpe_se=Decimal("0.081200"),
            min_backtest_length_days=252,
            multiple_testing_correction="Bonferroni",
        ),
        status="DONE",
        completed_at=datetime.now(UTC),
    )
