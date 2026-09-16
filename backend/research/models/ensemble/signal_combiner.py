"""Signal combination logic for ensemble direction and confidence."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.models.ensemble.kelly_sizer import half_kelly_capped


@dataclass(frozen=True)
class CombinedSignal:
    score: float
    confidence: float
    direction: str
    kelly_fraction: float


def direction_from_score(score: float) -> str:
    if score >= 0.65:
        return "STRONG_BUY"
    if score >= 0.2:
        return "BUY"
    if score <= -0.65:
        return "STRONG_SELL"
    if score <= -0.2:
        return "SELL"
    return "NEUTRAL"


def combine_weighted_signals(
    technical_score: float,
    ml_score: float,
    sentiment_tilt: float,
    regime: str,
    regime_mean: float,
    regime_variance: float,
) -> CombinedSignal:
    """Aggregate weighted signals and compute confidence/Kelly fraction."""
    fused_score = (0.4 * technical_score) + (0.6 * ml_score) + sentiment_tilt

    if regime in ("BEAR", "CRISIS") and fused_score > 0:
        fused_score = min(fused_score, 0.2)
    elif regime == "BULL" and fused_score < 0:
        fused_score = max(fused_score, -0.2)

    score = float(np.clip(fused_score, -1.0, 1.0))
    confidence = float(abs(score))

    return CombinedSignal(
        score=score,
        confidence=confidence,
        direction=direction_from_score(score),
        kelly_fraction=half_kelly_capped(score, confidence, regime_mean, regime_variance),
    )
