"""Dynamic ensemble weighting from rolling performance and regime priors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EnsembleWeights:
    """Container for model weights and confidence outputs."""

    weights: dict[str, float]
    confidence: float
    score: float


def rolling_sharpe_from_signals(signals: np.ndarray, actual_returns: np.ndarray) -> float:
    """Compute rolling Sharpe from signed returns.

    Args:
        signals: Vector of signal values in [-1, 1].
        actual_returns: Matching vector of realized returns.

    Returns:
        Annualized Sharpe ratio.
    """
    if signals.shape != actual_returns.shape:
        raise ValueError("signals and actual_returns must have same shape")
    signed_returns = np.sign(signals) * actual_returns
    std = float(np.std(signed_returns, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(signed_returns) / std * np.sqrt(252.0))


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp_v = np.exp(shifted)
    return exp_v / np.sum(exp_v)


def compute_dynamic_weights(
    rolling_sharpes: dict[str, float],
    regime_weights: dict[str, float],
) -> dict[str, float]:
    """Blend rolling Sharpe softmax with regime-conditioned priors.

    Formula:
        w_k(t) = 0.6 * softmax(SR_k(t)) + 0.4 * w_k_regime
    """
    models = list(rolling_sharpes.keys())
    sharpes = np.array([rolling_sharpes[m] for m in models], dtype=np.float64)
    sr_component = softmax(sharpes)
    reg_component = np.array([regime_weights.get(m, 0.0) for m in models], dtype=np.float64)
    if reg_component.sum() == 0:
        reg_component = np.ones_like(reg_component) / len(reg_component)
    else:
        reg_component = reg_component / reg_component.sum()

    blended = 0.6 * sr_component + 0.4 * reg_component
    blended = blended / blended.sum()
    return {model: float(weight) for model, weight in zip(models, blended, strict=True)}


def aggregate_signal(
    model_signals: dict[str, float],
    model_weights: dict[str, float],
) -> EnsembleWeights:
    """Compute ensemble score and confidence from model agreement.

    Confidence:
        C(t) = 1 - std(s_1..K(t)) / 2
    """
    models = sorted(model_signals.keys())
    values = np.array([model_signals[m] for m in models], dtype=np.float64)
    weights = np.array([model_weights.get(m, 0.0) for m in models], dtype=np.float64)
    if weights.sum() == 0:
        weights = np.ones_like(weights) / len(weights)
    else:
        weights = weights / weights.sum()

    score = float(np.sum(weights * values))
    confidence = float(np.clip(1.0 - np.std(values) / 2.0, 0.0, 1.0))
    return EnsembleWeights(weights={m: float(w) for m, w in zip(models, weights, strict=True)}, confidence=confidence, score=score)


def half_kelly_fraction(score: float, confidence: float, regime_mean: float, regime_variance: float) -> float:
    """Compute capped half-Kelly sizing fraction.

    Formula:
        f* = C(t) * S(t) * (mu_regime / sigma_regime^2)
        f_half = min(max(f*/2, 0), 0.25)
    """
    if regime_variance <= 0:
        raise ValueError("regime_variance must be > 0")
    full_kelly = confidence * score * (regime_mean / regime_variance)
    return float(np.clip(full_kelly / 2.0, 0.0, 0.25))
