"""Forecast utilities for state-dependent GARCH volatility."""

from __future__ import annotations

import numpy as np

from research.models.hmm_garch.garch import GarchParams


def forecast_state_garch_vol(last_sigma2: float, last_eps2: float, params: GarchParams, horizon_days: int) -> np.ndarray:
    """Forecast conditional volatility for n steps ahead.

    Uses recurrence sigma_t^2 = omega + alpha*eps_{t-1}^2 + beta*sigma_{t-1}^2,
    with expected future shock variance substituted by prior sigma^2.
    """
    h = max(int(horizon_days), 1)
    out = np.zeros(h)

    sigma2 = float(max(last_sigma2, 1e-12))
    eps2 = float(max(last_eps2, 0.0))
    for i in range(h):
        sigma2 = params.omega + params.alpha * eps2 + params.beta * sigma2
        sigma2 = max(sigma2, 1e-12)
        out[i] = np.sqrt(sigma2)
        eps2 = sigma2

    return out
