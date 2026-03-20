"""State-dependent GARCH(1,1) fitting and forecasting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

_EPS = 1e-10


@dataclass(slots=True)
class GarchParams:
    omega: float
    alpha: float
    beta: float


def garch_conditional_variance(eps: np.ndarray, params: GarchParams) -> np.ndarray:
    """Compute sigma_t^2 recursively for GARCH(1,1)."""
    e = np.asarray(eps, dtype=float).reshape(-1)
    n = len(e)
    sigma2 = np.zeros(n)
    sigma2[0] = max(np.var(e), _EPS)

    for t in range(1, n):
        sigma2[t] = params.omega + params.alpha * (e[t - 1] ** 2) + params.beta * sigma2[t - 1]
        sigma2[t] = max(sigma2[t], _EPS)

    return sigma2


def _nll(theta: np.ndarray, eps: np.ndarray) -> float:
    omega, alpha, beta = theta
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
        return 1e12

    sigma2 = garch_conditional_variance(eps, GarchParams(float(omega), float(alpha), float(beta)))
    return float(-np.sum(-0.5 * np.log(sigma2) - 0.5 * (eps**2 / sigma2)))


def fit_garch_11(eps: np.ndarray) -> GarchParams:
    """Fit GARCH(1,1) by minimizing negative log-likelihood with L-BFGS-B."""
    e = np.asarray(eps, dtype=float).reshape(-1)
    var = float(np.var(e) + _EPS)
    x0 = np.array([0.01 * var, 0.05, 0.9], dtype=float)

    bounds = [(1e-12, None), (0.0, 0.999), (0.0, 0.999)]
    result = minimize(_nll, x0=x0, args=(e,), method="L-BFGS-B", bounds=bounds)

    omega, alpha, beta = result.x
    if alpha + beta >= 0.999:
        beta = 0.999 - alpha
    return GarchParams(float(max(omega, _EPS)), float(max(alpha, 0.0)), float(max(beta, 0.0)))
