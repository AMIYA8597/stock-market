"""Evaluation metrics for TFT quantile forecasting."""

from __future__ import annotations

import numpy as np


def quantile_loss(y_true: np.ndarray, y_pred_q: np.ndarray, quantiles: tuple[float, ...] = (0.1, 0.5, 0.9)) -> float:
    """Pinball / quantile loss aggregated over quantiles and timesteps."""
    y = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred_q, dtype=float)
    if yp.shape[-1] != len(quantiles):
        raise ValueError("Last prediction dimension must match quantiles length")

    total = 0.0
    for i, q in enumerate(quantiles):
        err = y - yp[..., i]
        total += np.mean(np.maximum(q * err, (q - 1.0) * err))
    return float(total)


def winkler_score_coverage(y_true: np.ndarray, p10: np.ndarray, p90: np.ndarray, alpha: float = 0.2) -> tuple[float, float]:
    """Compute Winkler score and empirical interval coverage."""
    y = np.asarray(y_true, dtype=float)
    lo = np.asarray(p10, dtype=float)
    hi = np.asarray(p90, dtype=float)

    width = hi - lo
    below = y < lo
    above = y > hi

    penalty = np.where(below, (2.0 / alpha) * (lo - y), 0.0) + np.where(above, (2.0 / alpha) * (y - hi), 0.0)
    winkler = float(np.mean(width + penalty))
    coverage = float(np.mean((y >= lo) & (y <= hi)))
    return winkler, coverage
