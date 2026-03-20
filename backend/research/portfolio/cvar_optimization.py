"""CVaR portfolio optimizer using scenario tail minimization."""

from __future__ import annotations

import numpy as np


def optimize_cvar(returns: np.ndarray, alpha: float = 0.95, max_weight: float = 0.20) -> np.ndarray:
    """Approximate CVaR minimization via projected gradient on scenario losses."""
    r = np.asarray(returns, dtype=float)
    n_assets = r.shape[1]
    w = np.ones(n_assets) / n_assets

    for _ in range(400):
        portfolio_returns = r @ w
        losses = -portfolio_returns
        var = np.quantile(losses, alpha)
        tail_mask = losses >= var

        if not np.any(tail_mask):
            break

        grad = -np.mean(r[tail_mask], axis=0)
        w = w - 0.05 * grad
        w = np.clip(w, 0.0, max_weight)
        if w.sum() <= 0.0:
            w = np.ones(n_assets) / n_assets
        else:
            w = w / w.sum()

    return w
