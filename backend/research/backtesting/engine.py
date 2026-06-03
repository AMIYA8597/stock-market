"""Vectorized backtest engine based on matrix operations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.backtesting.cost_model import compute_costs


@dataclass(slots=True)
class BacktestResult:
    daily_returns: np.ndarray
    pnl: np.ndarray
    equity_curve: np.ndarray
    positions: np.ndarray
    costs: np.ndarray


def _rolling_std(x: np.ndarray, window: int = 21) -> np.ndarray:
    out = np.full_like(x, fill_value=np.nan, dtype=float)
    for t in range(window - 1, x.shape[0]):
        out[t] = np.std(x[t - window + 1 : t + 1], axis=0, ddof=1)
    return out


def _apply_constraints(pos: np.ndarray, max_gross: float = 2.0, max_net: float = 1.0, max_single: float = 0.20) -> np.ndarray:
    p = np.clip(pos, -max_single, max_single)

    gross = np.sum(np.abs(p), axis=1, keepdims=True)
    gross_scale = np.minimum(1.0, max_gross / np.where(gross <= 0, 1.0, gross))
    p = p * gross_scale

    net = np.sum(p, axis=1, keepdims=True)
    net_abs = np.abs(net)
    net_scale = np.minimum(1.0, max_net / np.where(net_abs <= 0, 1.0, net_abs))
    return p * net_scale


def run_vectorized_backtest(
    signals: np.ndarray,
    prices: np.ndarray,
    kelly_fraction: np.ndarray,
    initial_capital: float,
    adv: np.ndarray | None = None,
    target_vol: float = 0.15,
) -> BacktestResult:
    """Run matrix-based backtest without time-loop simulation logic."""
    s = np.asarray(signals, dtype=float)
    p = np.asarray(prices, dtype=float)
    k = np.asarray(kelly_fraction, dtype=float)

    if s.shape != p.shape or s.shape != k.shape:
        raise ValueError("signals, prices and kelly_fraction must share shape (T, N)")

    returns = np.zeros_like(p)
    returns[1:] = p[1:] / np.where(p[:-1] == 0.0, np.nan, p[:-1]) - 1.0
    returns = np.nan_to_num(returns, nan=0.0)

    pos_raw = s * k
    realized_vol = _rolling_std(returns, window=21) * np.sqrt(252.0)
    vol_scalar = target_vol / np.where(realized_vol <= 0.0, np.nan, realized_vol)
    vol_scalar = np.nan_to_num(vol_scalar, nan=1.0, posinf=1.0, neginf=1.0)

    pos_scaled = _apply_constraints(pos_raw * vol_scalar)

    trades = np.abs(np.diff(pos_scaled, axis=0, prepend=np.zeros((1, pos_scaled.shape[1]))))
    adv_mat = np.ones_like(p) if adv is None else np.asarray(adv, dtype=float)
    sell_mask = np.zeros_like(trades, dtype=bool)
    sell_mask[1:] = np.diff(pos_scaled, axis=0) < 0
    costs = compute_costs(trades, p, adv_mat, np.nan_to_num(realized_vol, nan=0.0), sell_mask=sell_mask)

    position_returns = np.zeros_like(returns)
    position_returns[1:] = pos_scaled[:-1] * returns[1:]

    pnl = np.sum(position_returns * initial_capital, axis=1) - np.sum(costs, axis=1)
    equity = initial_capital + np.cumsum(pnl)
    prev_equity = np.concatenate(([initial_capital], equity[:-1]))
    daily = np.where(prev_equity == 0.0, 0.0, np.diff(equity, prepend=[initial_capital]) / np.where(prev_equity == 0.0, 1.0, prev_equity))

    return BacktestResult(
        daily_returns=daily,
        pnl=pnl,
        equity_curve=equity,
        positions=pos_scaled,
        costs=np.sum(costs, axis=1),
    )
