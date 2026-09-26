"""
NeuroQuant ML Label Registry
"""

import hashlib
import inspect
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class LabelMeta:
    name: str
    func: Callable
    code_sha: str


_LABEL_REGISTRY: dict[str, LabelMeta] = {}

def label(name: str):
    """Decorator to register a label function."""
    def decorator(func: Callable):
        source = inspect.getsource(func)
        code_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]

        meta = LabelMeta(
            name=name,
            func=func,
            code_sha=code_sha
        )
        _LABEL_REGISTRY[name] = meta
        return func
    return decorator


def build_label(bars: pd.DataFrame, label_name: str) -> pd.Series:
    if label_name not in _LABEL_REGISTRY:
        raise ValueError(f"Unknown label: {label_name}")
    if "adj_close" not in bars.columns and "close" in bars.columns:
        bars = bars.assign(adj_close=bars["close"])
    elif "adj_close" not in bars.columns:
        raise ValueError("Bars missing 'adj_close' or 'close' column")

    meta = _LABEL_REGISTRY[label_name]
    result = meta.func(bars)

    if not result.index.equals(bars.index):
        raise ValueError(f"Label {label_name} returned a misaligned index")
    result.name = label_name
    return result
