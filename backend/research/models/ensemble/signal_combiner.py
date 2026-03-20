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
    if score > 0.6:
        return "STRONG_BUY"
    if score > 0.2:
        return "BUY"
    if score < -0.6:
        return "STRONG_SELL"
    if score < -0.2:
        return "SELL"
    return "NEUTRAL"


def combine_weighted_signals(
    model_signals: dict[str, float],
    model_weights: dict[str, float],
    regime_mean: float,
    regime_variance: float,
) -> CombinedSignal:
    """Aggregate weighted signals and compute confidence/Kelly fraction."""
    models = sorted(model_signals.keys())
    s = np.array([model_signals[m] for m in models], dtype=float)
    w = np.array([model_weights.get(m, 0.0) for m in models], dtype=float)

    if w.sum() <= 0.0:
        w = np.ones_like(w) / len(w)
    else:
        w = w / w.sum()

    score = float(np.sum(w * s))
    confidence = float(np.clip(1.0 - np.std(s) / 2.0, 0.0, 1.0))
    return CombinedSignal(
        score=score,
        confidence=confidence,
        direction=direction_from_score(score),
        kelly_fraction=half_kelly_capped(score, confidence, regime_mean, regime_variance),
    )
