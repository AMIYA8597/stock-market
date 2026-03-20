"""Real-time inference pipeline for ensemble signal production."""

from __future__ import annotations

from dataclasses import dataclass

from research.models.ensemble.orchestrator import EnsembleInferenceResult, InferenceContext, build_ensemble_result


@dataclass(slots=True)
class InferencePipelineInput:
    model_signals: dict[str, float]
    rolling_sharpes: dict[str, float]
    regime_weights: dict[str, float]
    regime_mean: float
    regime_variance: float


def run_inference_pipeline(payload: InferencePipelineInput) -> EnsembleInferenceResult:
    """Run deterministic ensemble aggregation for one inference tick."""
    return build_ensemble_result(
        InferenceContext(
            model_signals=payload.model_signals,
            rolling_sharpes=payload.rolling_sharpes,
            regime_weights=payload.regime_weights,
            regime_mean=payload.regime_mean,
            regime_variance=payload.regime_variance,
        )
    )
