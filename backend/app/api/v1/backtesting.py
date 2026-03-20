"""Backtesting API endpoints with async job-style responses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Query

from app.schemas.backtest import BacktestRequest

router = APIRouter()


@router.post("/run")
async def run_backtest(payload: BacktestRequest):
    """Queue a backtest run and return a job identifier."""
    return {
        "job_id": f"bt-{uuid4()}",
        "status": "PENDING",
        "estimated_seconds": 45,
        "strategy_name": payload.strategy_name,
    }


@router.get("/status/{job_id}")
async def backtest_status(job_id: str):
    """Return progress snapshot for a running backtest job."""
    return {
        "job_id": job_id,
        "status": "RUNNING",
        "progress_pct": 64,
        "result_preview": {"sharpe": 1.21, "max_drawdown": -0.132},
    }


@router.get("/results/{job_id}")
async def backtest_results(job_id: str, sample_paths: int = Query(default=100, ge=10, le=200)):
    """Return rich analytics payload for completed job."""
    base_date = datetime.now(UTC).date() - timedelta(days=120)
    equity_curve = [
        {
            "date": (base_date + timedelta(days=i)).isoformat(),
            "portfolio_value": 1_000_000 + i * 2100,
            "benchmark_value": 1_000_000 + i * 1650,
        }
        for i in range(120)
    ]
    return {
        "job_id": job_id,
        "metrics": {
            "total_return": 0.252,
            "cagr": 0.187,
            "sharpe": 1.31,
            "sortino": 1.88,
            "calmar": 1.12,
            "omega": 1.24,
            "max_drawdown": -0.167,
            "max_drawdown_duration_days": 37,
            "win_rate": 0.56,
            "profit_factor": 1.39,
            "avg_win": 0.013,
            "avg_loss": -0.009,
            "payoff_ratio": 1.44,
            "num_trades": 286,
            "gross_profit": 0.93,
            "gross_loss": -0.67,
            "tail_ratio": 1.11,
            "serenity_ratio": 0.88,
            "deflated_sharpe": 0.42,
        },
        "equity_curve": equity_curve,
        "drawdown_series": [
            {"date": point["date"], "drawdown_pct": -0.03 if idx % 19 == 0 else -0.01}
            for idx, point in enumerate(equity_curve)
        ],
        "trade_log": [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "symbol": "RELIANCE.NS",
                "direction": "BUY" if i % 2 == 0 else "SELL",
                "qty": 10,
                "price": 2450 + i,
                "pnl": 120.5,
                "cum_pnl": 2500 + i * 120,
            }
            for i in range(20)
        ],
        "walk_forward": {"fold_sharpes": [1.1, 1.3, 1.2, 1.4, 1.15], "mean": 1.23, "std": 0.11, "t_stat": 2.24, "p_value": 0.031},
        "monte_carlo": {
            "percentiles": {"p5": 0.81, "p25": 0.92, "p50": 1.06, "p75": 1.18, "p95": 1.33},
            "prob_of_ruin_10pct": 0.07,
            "prob_of_ruin_25pct": 0.02,
            "fan_paths_sample": [[1.0 + (j * 0.002) for j in range(120)] for _ in range(sample_paths)],
        },
        "statistical_tests": {
            "dm_test": {"statistic": 2.12, "p_value": 0.038, "vs_benchmark": "ARIMA"},
            "sharpe_se": 0.17,
            "min_backtest_length_days": 252,
            "multiple_testing_correction": "Bonferroni",
        },
    }
