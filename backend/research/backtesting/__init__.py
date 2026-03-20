"""Backtesting engine and analytics package."""

from research.backtesting.analytics import calmar_ratio, cagr, max_drawdown, omega_ratio, sharpe_ratio, sortino_ratio
from research.backtesting.cost_model import compute_costs
from research.backtesting.engine import BacktestResult, run_vectorized_backtest
from research.backtesting.monte_carlo import (
	MonteCarloResult,
	bootstrap_paths,
	merton_jump_diffusion_paths,
	summarize_monte_carlo,
)
from research.backtesting.statistical_tests import deflated_sharpe_ratio, diebold_mariano_test, min_backtest_length_days
from research.backtesting.walk_forward import CPCVSplit, evaluate_cpcv, generate_cpcv_splits

__all__ = [
	"BacktestResult",
	"CPCVSplit",
	"MonteCarloResult",
	"bootstrap_paths",
	"cagr",
	"calmar_ratio",
	"compute_costs",
	"deflated_sharpe_ratio",
	"diebold_mariano_test",
	"evaluate_cpcv",
	"generate_cpcv_splits",
	"max_drawdown",
	"merton_jump_diffusion_paths",
	"min_backtest_length_days",
	"omega_ratio",
	"run_vectorized_backtest",
	"sharpe_ratio",
	"sortino_ratio",
	"summarize_monte_carlo",
]
