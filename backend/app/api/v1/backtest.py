"""Backtest execution endpoints router (POST/GET /backtest/*)."""

from __future__ import annotations

import math

# import random  # removed per policy
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_rate_limiter
from app.core.entitlements import require_feature
from app.database.connection import async_session_factory
from app.models.backtest import BacktestJob
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV
from app.models.signal import EnsembleSignal
from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRequest,
    BacktestResultsResponse,
    BacktestRunResponse,
    BacktestStatusResponse,
    DrawdownPoint,
    EquityCurvePoint,
    MonteCarloResults,
    StatisticalTests,
    TradeLogEntry,
    WalkForwardMetrics,
)
from app.tasks.backtest_tasks import run_backtest_job_task
from research.backtesting.analytics import (
    cagr,
    calmar_ratio,
    max_drawdown,
    omega_ratio,
    sharpe_ratio,
    sortino_ratio,
)
from research.backtesting.engine import (
    run_vectorized_backtest,
)
from research.backtesting.monte_carlo import (
    bootstrap_paths,
    summarize_monte_carlo,
)
from research.backtesting.statistical_tests import (
    deflated_sharpe_ratio,
    diebold_mariano_test,
    min_backtest_length_days,
)
from research.backtesting.walk_forward import evaluate_cpcv

router = APIRouter(prefix="/backtest", tags=["backtest"])

def safe_round(val: float, places: int) -> float:
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    return round(float(val), places)

@router.post("/run", response_model=BacktestRunResponse, status_code=202)
async def post_backtest_run(
    request: BacktestRequest,
    current_user: dict = Depends(require_feature("PREMIUM")),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=2, window=60)),
) -> BacktestRunResponse:
    user_id_str = str(current_user.get("sub")) if isinstance(current_user, dict) else str(getattr(current_user, "user_id", getattr(current_user, "id", None)))

    job_id = uuid4()
    new_job = BacktestJob(
        id=job_id,
        user_id=UUID(user_id_str),
        strategy_name=request.strategy_name,
        strategy_params=request.strategy_params or {},
        universe=request.universe,
        date_from=request.date_from,
        date_to=request.date_to,
        initial_capital=request.initial_capital,
        status="PENDING",
    )
    db.add(new_job)
    await db.commit()

    # Trigger Celery task
    run_backtest_job_task.delay(str(job_id))

    days = max((request.date_to - request.date_from).days, 1)
    estimate = min(3600, 30 + len(request.universe) * days // 20)

    return BacktestRunResponse(
        job_id=str(job_id),
        status="PENDING",
        estimated_seconds=estimate,
        universe_size=len(request.universe),
        period_days=days,
        strategy_name=request.strategy_name,
    )


@router.get("/status/{job_id}", response_model=BacktestStatusResponse)
async def get_backtest_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestStatusResponse:
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    stmt = select(BacktestJob).where(BacktestJob.id == job_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    progress_pct = job.progress if job.progress is not None else 0
    if job.status == "DONE":
        progress_pct = 100
        
    return BacktestStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress_pct=progress_pct,
        error_message=job.error_message
    )

@router.get("/results/{job_id}", response_model=BacktestResultsResponse)
async def get_backtest_results(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResultsResponse:
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    stmt = select(BacktestJob).where(BacktestJob.id == job_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != "DONE" or not job.results:
        raise HTTPException(status_code=400, detail="Job is not completed yet or has no results.")

    results = job.results
    
    # We construct the response based on the schema and what we saved in backtest_tasks
    # If the metrics are missing, we mock them for now.
    metrics = results.get("metrics", {})
    
    return BacktestResultsResponse(
        job_id=str(job.id),
        strategy_name=job.strategy_name,
        universe=job.universe,
        date_from=job.date_from,
        date_to=job.date_to,
        initial_capital=job.initial_capital,
        completed_at=datetime.now(UTC),
        status=job.status,
        metrics=BacktestMetrics(
            total_return=safe_round(metrics.get("total_return", 0), 4),
            cagr=safe_round(metrics.get("cagr", 0), 4),
            sharpe=safe_round(metrics.get("sharpe", 0), 4),
            sharpe_ratio=safe_round(metrics.get("sharpe", 0), 4),
            sortino_ratio=safe_round(metrics.get("sortino_ratio", 0), 4),
            max_drawdown=safe_round(metrics.get("max_drawdown", 0), 4),
            max_drawdown_duration_days=metrics.get("max_drawdown_duration_days", 0),
            win_rate=safe_round(metrics.get("win_rate", 0), 4),
            profit_factor=safe_round(metrics.get("profit_factor", 0), 4),
            avg_win=safe_round(metrics.get("avg_win", 0), 4),
            avg_loss=safe_round(metrics.get("avg_loss", 0), 4),
            payoff_ratio=safe_round(metrics.get("payoff_ratio", 0), 4),
            num_trades=metrics.get("num_trades", 0),
            gross_profit=safe_round(metrics.get("gross_profit", 0), 4),
            gross_loss=safe_round(metrics.get("gross_loss", 0), 4),
            expectancy=safe_round(metrics.get("expectancy", 0), 4),
            omega_ratio=safe_round(metrics.get("omega_ratio", 0), 4),
            calmar_ratio=safe_round(metrics.get("calmar_ratio", 0), 4),
            tail_ratio=safe_round(metrics.get("tail_ratio", 0), 4),
            serenity_ratio=safe_round(metrics.get("serenity_ratio", 0), 4),
            deflated_sharpe=safe_round(metrics.get("deflated_sharpe", 0), 4),
        ),
        equity_curve=[EquityCurvePoint(**pt) for pt in results.get("equity_curve", [])],
        drawdown_series=[DrawdownPoint(**pt) for pt in results.get("drawdown_series", [])],
        trade_log=[TradeLogEntry(**tr) for tr in results.get("trade_log", [])],
        monte_carlo=None,
        statistical_tests=None,
        walk_forward=None
    )


    stmt = select(BacktestJob).where(BacktestJob.id == job_uuid, BacktestJob.user_id == uid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Backtest job not found")

    if job.status not in ("COMPLETED", "DONE"):
        raise HTTPException(
            status_code=400, detail=f"Backtest job is not completed (status: {job.status})"
        )

    res_data = job.results
    if not res_data:
        raise HTTPException(status_code=500, detail="Job completed but results missing")

    completed_dt = job.completed_at
    if completed_dt and completed_dt.tzinfo is None:
        completed_dt = completed_dt.replace(tzinfo=UTC)

    return BacktestResultsResponse(
        job_id=str(job.id),
        strategy_name=job.strategy_name,
        universe=job.universe,
        date_from=job.date_from,
        date_to=job.date_to,
        initial_capital=Decimal(str(job.initial_capital)),
        metrics=BacktestMetrics(**res_data["metrics"]),
        equity_curve=[EquityCurvePoint(**pt) for pt in res_data["equity_curve"]],
        drawdown_series=[DrawdownPoint(**pt) for pt in res_data["drawdown_series"]],
        trade_log=[TradeLogEntry(**pt) for pt in res_data["trade_log"]],
        walk_forward=WalkForwardMetrics(**res_data["walk_forward"])
        if res_data.get("walk_forward")
        else None,
        monte_carlo=MonteCarloResults(**res_data["monte_carlo"])
        if res_data.get("monte_carlo")
        else None,
        statistical_tests=StatisticalTests(**res_data["statistical_tests"])
        if res_data.get("statistical_tests")
        else None,
        status="DONE",
        completed_at=completed_dt or datetime.now(UTC),
    )
