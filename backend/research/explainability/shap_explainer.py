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


def get_tree_shap(
    model, feature_matrix: np.ndarray, feature_names: list[str] | None = None
) -> ShapExplanation:
    """Compute true SHAP values using shap.TreeExplainer."""
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(feature_matrix)

    # Handle multi-class (returns list of arrays) vs binary (returns single array)
    if isinstance(shap_values, list):
        # Default to positive class for binary classification represented as multi-class
        shap_values = shap_values[1]

    # Handle TreeExplainer's expected_value format
    base_value = explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = float(base_value[1] if len(base_value) > 1 else base_value[0])
    else:
        base_value = float(base_value)

    if feature_names is None:
        feature_names = [f"f_{i}" for i in range(feature_matrix.shape[1])]

    return ShapExplanation(values=shap_values, base_value=base_value, feature_names=feature_names)


def top_contributors(
    expl: ShapExplanation, row_index: int, top_k: int = 10
) -> list[tuple[str, float]]:
    """Return top absolute SHAP contributors for one row."""
    row = expl.values[row_index]
    idx = np.argsort(np.abs(row))[::-1][:top_k]
    return [(expl.feature_names[i], float(row[i])) for i in idx]
