"""Transaction cost model for vectorized backtests."""

from __future__ import annotations

import numpy as np


def compute_costs(
    trades_abs: np.ndarray,
    prices: np.ndarray,
    adv: np.ndarray,
    realized_vol: np.ndarray,
    sell_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Compute brokerage, STT and impact costs.

    Args:
        trades_abs: Absolute position change matrix (T, N).
        prices: Price matrix (T, N).
        adv: Average daily volume matrix (T, N).
        realized_vol: Realized volatility matrix (T, N).
        sell_mask: Optional boolean mask where sell-side STT applies.

    Returns:
        Total cost matrix (T, N).
    """
    trade_notional = trades_abs * prices
    brokerage = trade_notional * 0.0003

    if sell_mask is None:
        stt = trade_notional * 0.00025
    else:
        stt = trade_notional * 0.00025 * sell_mask.astype(float)

    safe_adv = np.where(adv <= 0.0, 1e-12, adv)
    impact = np.sqrt(trades_abs / safe_adv) * prices * realized_vol * 0.1

    return brokerage + stt + np.nan_to_num(impact, nan=0.0, posinf=0.0, neginf=0.0)
