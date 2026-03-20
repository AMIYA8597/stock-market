"""Vectorized performance analytics for systematic strategy evaluation."""

from __future__ import annotations

import numpy as np


def sharpe_ratio(returns: np.ndarray, rf_daily: float = 0.0) -> float:
    excess = returns - rf_daily
    sigma = float(np.std(excess, ddof=1))
    if sigma == 0.0:
        return 0.0
    return float(np.mean(excess) / sigma * np.sqrt(252.0))


def sortino_ratio(returns: np.ndarray, rf_daily: float = 0.0) -> float:
    excess = returns - rf_daily
    downside = np.minimum(excess, 0.0)
    downside_std = float(np.std(downside, ddof=1))
    if downside_std == 0.0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(252.0))


def max_drawdown(equity_curve: np.ndarray) -> tuple[float, int]:
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = equity_curve / running_max - 1.0
    min_idx = int(np.argmin(drawdown))
    max_dd = float(drawdown[min_idx])

    duration = 0
    current = 0
    for dd in drawdown:
        if dd < 0:
            current += 1
            duration = max(duration, current)
        else:
            current = 0

    return max_dd, duration


def cagr(equity_curve: np.ndarray) -> float:
    if len(equity_curve) < 2:
        return 0.0
    years = len(equity_curve) / 252.0
    if years <= 0:
        return 0.0
    return float((equity_curve[-1] / equity_curve[0]) ** (1.0 / years) - 1.0)


def calmar_ratio(equity_curve: np.ndarray) -> float:
    growth = cagr(equity_curve)
    dd, _ = max_drawdown(equity_curve)
    if dd == 0:
        return 0.0
    return float(growth / abs(dd))


def omega_ratio(returns: np.ndarray, threshold: float = 0.0) -> float:
    gains = np.maximum(returns - threshold, 0.0)
    losses = np.maximum(threshold - returns, 0.0)
    den = float(np.sum(losses))
    if den == 0.0:
        return float("inf")
    return float(np.sum(gains) / den)
