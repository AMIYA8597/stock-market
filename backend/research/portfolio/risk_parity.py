"""Equal risk contribution (risk parity) optimizer."""

from __future__ import annotations

import numpy as np


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    sigma = np.asarray(cov, dtype=float)
    w = np.asarray(weights, dtype=float)
    port_vol = np.sqrt(max(float(w.T @ sigma @ w), 1e-12))
    mrc = sigma @ w / port_vol
    return w * mrc


def risk_parity_weights(cov: np.ndarray, max_iter: int = 500, tol: float = 1e-8) -> np.ndarray:
    """Solve for equal risk contribution weights via multiplicative updates."""
    sigma = np.asarray(cov, dtype=float)
    n = sigma.shape[0]
    w = np.ones(n) / n

    for _ in range(max_iter):
        rc = risk_contributions(w, sigma)
        target = np.mean(rc)
        ratio = np.where(rc <= 1e-12, 1.0, target / rc)
        w_new = np.clip(w * ratio, 1e-8, None)
        w_new = w_new / w_new.sum()

        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break
        w = w_new

    return w
