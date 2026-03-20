"""Black-Litterman posterior construction with ML signal views."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.portfolio.mean_variance import optimize_mean_variance


@dataclass(slots=True)
class BlackLittermanPosterior:
    posterior_returns: np.ndarray
    posterior_covariance: np.ndarray


def black_litterman_posterior(
    cov: np.ndarray,
    market_weights: np.ndarray,
    signals: np.ndarray,
    confidence: np.ndarray,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    target_vol: float = 0.15,
) -> BlackLittermanPosterior:
    """Build BL posterior using absolute views from ensemble signals."""
    sigma = np.asarray(cov, dtype=float)
    w_mkt = np.asarray(market_weights, dtype=float)
    s = np.asarray(signals, dtype=float)
    c = np.asarray(confidence, dtype=float)

    n = sigma.shape[0]
    pi = risk_aversion * sigma @ w_mkt

    q = s * target_vol / np.sqrt(252.0)
    p = np.eye(n)

    var_pi = np.diag(sigma)
    omega_diag = (1.0 - np.clip(np.abs(c), 0.0, 1.0)) * var_pi
    omega = np.diag(np.where(omega_diag <= 1e-12, 1e-12, omega_diag))

    tau_sigma = tau * sigma
    m = np.linalg.inv(np.linalg.inv(tau_sigma) + p.T @ np.linalg.inv(omega) @ p)
    mu_bl = m @ (np.linalg.inv(tau_sigma) @ pi + p.T @ np.linalg.inv(omega) @ q)
    sigma_bl = sigma + m

    return BlackLittermanPosterior(posterior_returns=mu_bl, posterior_covariance=sigma_bl)


def optimize_black_litterman(
    cov: np.ndarray,
    market_weights: np.ndarray,
    signals: np.ndarray,
    confidence: np.ndarray,
    risk_aversion: float = 2.5,
    max_weight: float = 0.20,
) -> tuple[np.ndarray, BlackLittermanPosterior]:
    """Optimize portfolio weights using BL posterior moments."""
    posterior = black_litterman_posterior(
        cov=cov,
        market_weights=market_weights,
        signals=signals,
        confidence=confidence,
        risk_aversion=risk_aversion,
    )
    w = optimize_mean_variance(
        exp_returns=posterior.posterior_returns,
        cov=posterior.posterior_covariance,
        risk_aversion=risk_aversion,
        max_weight=max_weight,
    )
    return w, posterior
