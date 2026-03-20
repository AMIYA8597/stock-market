"""Parallel multi-model inference orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import numpy as np

from research.models.ensemble.signal_combiner import CombinedSignal, combine_weighted_signals
from research.models.ensemble.weight_manager import compute_dynamic_weights


@dataclass(slots=True)
class InferenceContext:
    model_signals: dict[str, float]
    rolling_sharpes: dict[str, float]
    regime_weights: dict[str, float]
    regime_mean: float
    regime_variance: float


@dataclass(slots=True)
class EnsembleInferenceResult:
    combined: CombinedSignal
    model_weights: dict[str, float]
    model_signals: dict[str, float]


async def _run_callable(maybe_async_callable: Any, *args: Any, **kwargs: Any) -> Any:
    result = maybe_async_callable(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return await asyncio.to_thread(lambda: result)


async def run_parallel_inference(model_calls: dict[str, tuple[Any, tuple[Any, ...], dict[str, Any]]]) -> dict[str, float]:
    """Run model inference calls concurrently and normalize into scalar signals.

    Input mapping format:
      model_name -> (callable, args_tuple, kwargs_dict)
    """
    tasks = {
        name: asyncio.create_task(_run_callable(call, *args, **kwargs))
        for name, (call, args, kwargs) in model_calls.items()
    }

    outputs: dict[str, float] = {}
    for name, task in tasks.items():
        value = await task
        if isinstance(value, np.ndarray):
            outputs[name] = float(np.mean(value))
        elif isinstance(value, dict):
            outputs[name] = float(np.mean(list(value.values()))) if value else 0.0
        else:
            outputs[name] = float(value)
    return outputs


def build_ensemble_result(ctx: InferenceContext) -> EnsembleInferenceResult:
    """Compute weights and final combined signal from model outputs."""
    weights = compute_dynamic_weights(ctx.rolling_sharpes, ctx.regime_weights)
    combined = combine_weighted_signals(
        model_signals=ctx.model_signals,
        model_weights=weights,
        regime_mean=ctx.regime_mean,
        regime_variance=ctx.regime_variance,
    )
    return EnsembleInferenceResult(combined=combined, model_weights=weights, model_signals=ctx.model_signals)
