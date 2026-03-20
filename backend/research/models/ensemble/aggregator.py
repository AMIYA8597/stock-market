"""End-to-end ensemble decision builder from model outputs."""

from __future__ import annotations

from dataclasses import dataclass

from research.models.ensemble.weight_manager import (
    EnsembleWeights,
    aggregate_signal,
    compute_dynamic_weights,
    half_kelly_fraction,
)


@dataclass(frozen=True)
class EnsembleDecision:
    score: float
    confidence: float
    direction: str
    kelly_fraction: float
    weights: dict[str, float]


def _direction_from_score(score: float) -> str:
    if score >= 0.6:
        return "STRONG_BUY"
    if score >= 0.2:
        return "BUY"
    if score <= -0.6:
        return "STRONG_SELL"
    if score <= -0.2:
        return "SELL"
    return "NEUTRAL"


def build_ensemble_decision(
    model_signals: dict[str, float],
    rolling_sharpes: dict[str, float],
    regime_weights: dict[str, float],
    regime_mean: float,
    regime_variance: float,
) -> EnsembleDecision:
    """Compute dynamic weights, aggregate signal, and position size in one call."""
    weights = compute_dynamic_weights(rolling_sharpes=rolling_sharpes, regime_weights=regime_weights)
    agg: EnsembleWeights = aggregate_signal(model_signals=model_signals, model_weights=weights)
    kelly = half_kelly_fraction(
        score=agg.score,
        confidence=agg.confidence,
        regime_mean=regime_mean,
        regime_variance=regime_variance,
    )
    return EnsembleDecision(
        score=agg.score,
        confidence=agg.confidence,
        direction=_direction_from_score(agg.score),
        kelly_fraction=kelly,
        weights=agg.weights,
    )
