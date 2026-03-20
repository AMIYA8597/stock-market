"""Mean-variance optimization with Ledoit-Wolf covariance shrinkage."""

from __future__ import annotations

import numpy as np


def ledoit_wolf_shrinkage(returns: np.ndarray) -> np.ndarray:
    """Compute Ledoit-Wolf shrunk covariance estimator.

    Σ_hat = δ F + (1 - δ) S
    F = (trace(S) / N) I
    """
    x = np.asarray(returns, dtype=float)
    x = x - np.mean(x, axis=0, keepdims=True)
    t, n = x.shape

    s = (x.T @ x) / t
    f = (np.trace(s) / n) * np.eye(n)

    num = 0.0
    for i in range(t):
        outer = np.outer(x[i], x[i])
        num += np.sum((outer - s) ** 2)
    num = num / (t**2)

    den = np.sum((f - s) ** 2)
    delta = 1.0 if den <= 1e-12 else min(num / den, 1.0)
    return delta * f + (1.0 - delta) * s


def optimize_mean_variance(
    exp_returns: np.ndarray,
    cov: np.ndarray,
    risk_aversion: float = 2.5,
    max_weight: float = 0.20,
) -> np.ndarray:
    """Closed-form mean-variance proxy with projection to simplex constraints."""
    mu = np.asarray(exp_returns, dtype=float)
    sigma = np.asarray(cov, dtype=float)

    inv = np.linalg.pinv(sigma)
    raw = inv @ mu / max(risk_aversion, 1e-8)

    w = np.clip(raw, 0.0, max_weight)
    if w.sum() <= 0.0:
        w = np.ones_like(w) / len(w)
    else:
        w = w / w.sum()
    return w
