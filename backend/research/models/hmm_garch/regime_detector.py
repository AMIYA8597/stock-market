"""Regime detector by combining HMM posteriors and state GARCH dynamics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.models.hmm_garch.forecaster import forecast_state_garch_vol
from research.models.hmm_garch.garch import GarchParams, fit_garch_11, garch_conditional_variance
from research.models.hmm_garch.hmm import StudentTHMM


@dataclass(slots=True)
class RegimeDetectionResult:
    states: np.ndarray
    posterior_probs: np.ndarray
    conditional_vol: np.ndarray
    forecast_5d: np.ndarray
    forecast_21d: np.ndarray
    state_garch_params: dict[int, GarchParams]


def detect_regime(returns: np.ndarray, hmm: StudentTHMM | None = None) -> RegimeDetectionResult:
    """Run HMM + per-state GARCH fit and produce regime diagnostics."""
    r = np.asarray(returns, dtype=float).reshape(-1)
    model = hmm or StudentTHMM(n_states=4)
    if not hasattr(model, "fitted") or not model.fitted:
        model.fit(r)
        model.fitted = True

    states = model.viterbi(r)
    probs = model.posterior(r)

    state_params: dict[int, GarchParams] = {}
    cond_vol = np.zeros_like(r)

    for k in range(model.n_states):
        idx = np.where(states == k)[0]
        if len(idx) < 30:
            state_params[k] = GarchParams(omega=1e-6, alpha=0.05, beta=0.9)
            continue

        eps_k = r[idx] - model.mu_[k]
        params = fit_garch_11(eps_k)
        state_params[k] = params

        sigma2_k = garch_conditional_variance(eps_k, params)
        cond_vol[idx] = np.sqrt(sigma2_k)

    # Fill missing vols from nearest non-zero values.
    if np.any(cond_vol == 0.0):
        nz = cond_vol[cond_vol > 0]
        fallback = float(np.mean(nz)) if len(nz) > 0 else float(np.std(r))
        cond_vol[cond_vol == 0.0] = fallback

    current_state = int(states[-1])
    current_params = state_params[current_state]
    last_eps2 = float((r[-1] - model.mu_[current_state]) ** 2)
    last_sigma2 = float(cond_vol[-1] ** 2)

    forecast_5d = forecast_state_garch_vol(last_sigma2, last_eps2, current_params, 5)
    forecast_21d = forecast_state_garch_vol(last_sigma2, last_eps2, current_params, 21)

    return RegimeDetectionResult(
        states=states,
        posterior_probs=probs,
        conditional_vol=cond_vol,
        forecast_5d=forecast_5d,
        forecast_21d=forecast_21d,
        state_garch_params=state_params,
    )
