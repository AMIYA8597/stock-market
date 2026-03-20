"""Statistical tests for forecast and strategy evaluation."""

from __future__ import annotations

import math

import numpy as np


def diebold_mariano_test(loss_a: np.ndarray, loss_b: np.ndarray) -> tuple[float, float]:
    """Compute one-step DM statistic and two-sided p-value (normal approx)."""
    la = np.asarray(loss_a, dtype=float)
    lb = np.asarray(loss_b, dtype=float)
    if la.shape != lb.shape:
        raise ValueError("loss arrays must have same shape")

    d = la - lb
    mean_d = float(np.mean(d))
    var_d = float(np.var(d, ddof=1))
    if var_d <= 0.0:
        return 0.0, 1.0

    dm = mean_d / math.sqrt(var_d / len(d))
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(dm) / math.sqrt(2.0))))
    return dm, p


def deflated_sharpe_ratio(sharpe: float, n_trials: int) -> float:
    """Compute deflated Sharpe ratio proxy with multiple-testing adjustment."""
    if n_trials <= 1:
        return sharpe
    e_sr_max = (0.5772156649 + math.sqrt(2.0 * math.log(n_trials))) / (2.0 * math.sqrt(math.log(n_trials)))
    return sharpe - e_sr_max


def min_backtest_length_days(target_sharpe: float, sharpe_se: float, z_alpha: float = 1.96) -> int:
    """Estimate minimum sample length for statistically significant Sharpe."""
    if target_sharpe <= 0 or sharpe_se <= 0:
        return 0
    n = (z_alpha * sharpe_se / target_sharpe) ** 2
    return int(math.ceil(n))
