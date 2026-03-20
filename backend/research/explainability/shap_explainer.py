"""SHAP utilities for tree and deep models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class ShapExplanation:
    values: np.ndarray
    base_value: float
    feature_names: list[str]


def approximate_tree_shap(
    feature_matrix: np.ndarray,
    feature_importance: np.ndarray,
    base_value: float = 0.0,
    feature_names: list[str] | None = None,
) -> ShapExplanation:
    """Compute a deterministic SHAP-like attribution proxy for tabular models."""
    x = np.asarray(feature_matrix, dtype=float)
    imp = np.asarray(feature_importance, dtype=float)
    mean_x = np.mean(x, axis=0, keepdims=True)
    values = (x - mean_x) * imp

    if feature_names is None:
        feature_names = [f"f_{i}" for i in range(x.shape[1])]
    return ShapExplanation(values=values, base_value=float(base_value), feature_names=feature_names)


def top_contributors(expl: ShapExplanation, row_index: int, top_k: int = 10) -> list[tuple[str, float]]:
    """Return top absolute SHAP contributors for one row."""
    row = expl.values[row_index]
    idx = np.argsort(np.abs(row))[::-1][:top_k]
    return [(expl.feature_names[i], float(row[i])) for i in idx]
