"""Kelly-based position sizing utilities."""

from __future__ import annotations


def kelly_fraction(score: float, confidence: float, regime_mean: float, regime_variance: float) -> float:
    """Compute unconstrained Kelly fraction.

    f* = C(t) * S(t) * (mu_regime / sigma_regime^2)
    """
    if regime_variance <= 0:
        raise ValueError("regime_variance must be > 0")
    return confidence * score * (regime_mean / regime_variance)


def half_kelly_capped(score: float, confidence: float, regime_mean: float, regime_variance: float, cap: float = 0.25) -> float:
    """Compute capped half-Kelly sizing in [0, cap]."""
    f_full = kelly_fraction(score, confidence, regime_mean, regime_variance)
    f_half = f_full / 2.0
    return max(0.0, min(cap, f_half))
