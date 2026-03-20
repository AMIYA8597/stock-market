"""Monte Carlo simulation utilities for strategy robustness analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class MonteCarloResult:
    paths: np.ndarray
    percentiles: dict[str, float]
    prob_ruin_10pct: float
    prob_ruin_25pct: float


def bootstrap_paths(returns: np.ndarray, n_simulations: int = 10_000, random_seed: int = 42) -> np.ndarray:
    """Bootstrap return paths by iid resampling empirical returns."""
    r = np.asarray(returns, dtype=float).reshape(-1)
    rng = np.random.default_rng(random_seed)
    idx = rng.integers(0, len(r), size=(n_simulations, len(r)))
    return r[idx]


def merton_jump_diffusion_paths(
    mu: float,
    sigma: float,
    lambda_jump: float,
    jump_mu: float,
    jump_sigma: float,
    horizon_days: int,
    n_simulations: int = 10_000,
    dt: float = 1 / 252,
    random_seed: int = 42,
) -> np.ndarray:
    """Simulate return paths under Merton jump-diffusion dynamics."""
    rng = np.random.default_rng(random_seed)
    z = rng.normal(size=(n_simulations, horizon_days))
    n_jump = rng.poisson(lambda_jump * dt, size=(n_simulations, horizon_days))
    j = rng.normal(jump_mu, jump_sigma, size=(n_simulations, horizon_days))

    diffusion = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    jumps = n_jump * j
    return diffusion + jumps


def summarize_monte_carlo(daily_returns_paths: np.ndarray, initial_capital: float = 1.0) -> MonteCarloResult:
    """Summarize MC path distribution by terminal equity percentiles and ruin odds."""
    r = np.asarray(daily_returns_paths, dtype=float)
    equity_paths = initial_capital * np.cumprod(1.0 + r, axis=1)
    terminal = equity_paths[:, -1]

    percentiles = {
        "p5": float(np.percentile(terminal, 5)),
        "p25": float(np.percentile(terminal, 25)),
        "p50": float(np.percentile(terminal, 50)),
        "p75": float(np.percentile(terminal, 75)),
        "p95": float(np.percentile(terminal, 95)),
    }
    prob_10 = float(np.mean(np.min(equity_paths, axis=1) <= initial_capital * 0.90))
    prob_25 = float(np.mean(np.min(equity_paths, axis=1) <= initial_capital * 0.75))
    return MonteCarloResult(
        paths=equity_paths,
        percentiles=percentiles,
        prob_ruin_10pct=prob_10,
        prob_ruin_25pct=prob_25,
    )
