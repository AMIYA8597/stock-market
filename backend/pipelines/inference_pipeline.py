"""Real-time inference pipeline for ensemble signal production."""

from __future__ import annotations

from dataclasses import dataclass

from research.models.ensemble.orchestrator import (
    EnsembleInferenceResult,
    InferenceContext,
    build_ensemble_result,
)


@dataclass(slots=True)
class InferencePipelineInput:
    technical_score: float
    ml_score: float
    sentiment_tilt: float
    regime: str
    regime_mean: float
    regime_variance: float


def run_inference_pipeline(payload: InferencePipelineInput) -> EnsembleInferenceResult:
    """Run deterministic ensemble aggregation for one inference tick."""
    return build_ensemble_result(
        InferenceContext(
            technical_score=payload.technical_score,
            ml_score=payload.ml_score,
            sentiment_tilt=payload.sentiment_tilt,
            regime=payload.regime,
            regime_mean=payload.regime_mean,
            regime_variance=payload.regime_variance,
        )
    )
