"""
NeuroQuant ML Feature Registry
"""

import hashlib
import inspect
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd


@dataclass
class FeatureMeta:
    name: str
    family: str
    params: dict[str, Any]
    warmup: int
    dtype: str
    func: Callable
    code_sha: str


_FEATURE_REGISTRY: dict[str, FeatureMeta] = {}
_FEATURE_SETS = {"fs_v1"}


def feature(name: str, family: str, params: dict[str, Any], warmup: int, dtype: str = "float32"):
    """Decorator to register a pure causal feature function."""
    def decorator(func: Callable):
        source = inspect.getsource(func)
        code_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]

        meta = FeatureMeta(
            name=name,
            family=family,
            params=params,
            warmup=warmup,
            dtype=dtype,
            func=func,
            code_sha=code_sha
        )
        _FEATURE_REGISTRY[name] = meta
        return func
    return decorator


def list_features(feature_set_id: str | None = None) -> list[str]:
    """Return the registered features for a known feature set."""
    if feature_set_id is not None and feature_set_id not in _FEATURE_SETS:
        raise ValueError(f"Unknown feature set: {feature_set_id}")
    return sorted(_FEATURE_REGISTRY)


def build_features(bars: pd.DataFrame, feature_set_id: str) -> pd.DataFrame:
    """
    Compute features over OHLCV bars.
    bars must have columns: open, high, low, close, volume.
    Returns a DataFrame containing only the computed features, aligned to dates.
    """
    if feature_set_id not in _FEATURE_SETS:
        raise ValueError(f"Unknown feature set: {feature_set_id}")
    required = {"open", "high", "low", "close", "volume"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"Bars are missing required columns: {missing}")
    features_df = pd.DataFrame(index=bars.index)

    # Sort features by name for determinism
    for name in sorted(_FEATURE_REGISTRY.keys()):
        meta = _FEATURE_REGISTRY[name]

        # Compute feature
        result = meta.func(bars)

        if not result.index.equals(bars.index):
            raise ValueError(f"Feature {name} returned a misaligned index")
        if isinstance(result, pd.Series):
            features_df[name] = result.astype(meta.dtype)
        elif isinstance(result, pd.DataFrame):
            for col in result.columns:
                if col in features_df:
                    raise ValueError(f"Duplicate feature output: {col}")
                features_df[col] = result[col].astype(meta.dtype)
        else:
            raise TypeError(f"Feature {name} must return a Series or DataFrame")

    return features_df
