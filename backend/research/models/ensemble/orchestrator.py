"""Parallel multi-model inference orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
import numpy as np

from research.models.ensemble.signal_combiner import CombinedSignal, combine_weighted_signals

@dataclass(slots=True)
class InferenceContext:
    technical_score: float
    ml_score: float
    sentiment_tilt: float
    regime: str
    regime_mean: float
    regime_variance: float

@dataclass(slots=True)
class EnsembleInferenceResult:
    combined: CombinedSignal

async def _run_callable(maybe_async_callable: Any, *args: Any, **kwargs: Any) -> Any:
    result = maybe_async_callable(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return await asyncio.to_thread(lambda: result)

async def run_parallel_inference(
    model_calls: dict[str, tuple[Any, tuple[Any, ...], dict[str, Any]]],
) -> dict[str, float]:
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
    """Compute final combined signal from model outputs."""
    combined = combine_weighted_signals(
        technical_score=ctx.technical_score,
        ml_score=ctx.ml_score,
        sentiment_tilt=ctx.sentiment_tilt,
        regime=ctx.regime,
        regime_mean=ctx.regime_mean,
        regime_variance=ctx.regime_variance,
    )
    return EnsembleInferenceResult(combined=combined)
