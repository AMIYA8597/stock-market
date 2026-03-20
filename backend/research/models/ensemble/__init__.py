"""Dynamic ensemble weighting and signal aggregation algorithms."""

from research.models.ensemble.aggregator import EnsembleDecision, build_ensemble_decision
from research.models.ensemble.kelly_sizer import half_kelly_capped, kelly_fraction
from research.models.ensemble.orchestrator import (
    EnsembleInferenceResult,
    InferenceContext,
    build_ensemble_result,
    run_parallel_inference,
)
from research.models.ensemble.signal_combiner import CombinedSignal, combine_weighted_signals, direction_from_score
from research.models.ensemble.weight_manager import (
	EnsembleWeights,
	aggregate_signal,
	compute_dynamic_weights,
	half_kelly_fraction,
	rolling_sharpe_from_signals,
)

__all__ = [
	"EnsembleDecision",
	"EnsembleInferenceResult",
	"EnsembleWeights",
	"CombinedSignal",
	"aggregate_signal",
	"build_ensemble_decision",
	"build_ensemble_result",
	"combine_weighted_signals",
	"compute_dynamic_weights",
	"direction_from_score",
	"half_kelly_capped",
	"half_kelly_fraction",
	"InferenceContext",
	"kelly_fraction",
	"run_parallel_inference",
	"rolling_sharpe_from_signals",
]
