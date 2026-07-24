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


def trade_metrics(pnl: np.ndarray) -> tuple[float, float, float]:
    """Calculate win rate, profit factor, and expectancy.
    Args:
        pnl: Array of per-trade PnL (or daily PnL where trade happened).
    Returns:
        (win_rate, profit_factor, expectancy)
    """
    trades = pnl[pnl != 0]
    if len(trades) == 0:
        return 0.0, 0.0, 0.0

    wins = trades[trades > 0]
    losses = trades[trades < 0]

    win_rate = len(wins) / len(trades)

    gross_profit = np.sum(wins)
    gross_loss = np.abs(np.sum(losses))

    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    expectancy = float(np.mean(trades))

    return float(win_rate), profit_factor, expectancy


def calculate_turnover(positions: np.ndarray, prices: np.ndarray, initial_capital: float) -> float:
    """Calculate annualized portfolio turnover."""
    if len(positions) < 2:
        return 0.0

    # Notional value of trades
    trades = np.abs(np.diff(positions, prepend=0))
    notional_traded = trades * prices

    total_turnover = np.sum(notional_traded)
    years = len(positions) / 252.0

    if years <= 0:
        return 0.0

    annualized_turnover = (total_turnover / 2.0) / initial_capital / years
    return float(annualized_turnover)
