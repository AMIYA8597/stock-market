"""Counterfactual generation by minimal feature perturbations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Counterfactual:
    features: np.ndarray
    distance: float
    target_score: float


def generate_counterfactuals_linear(
    x: np.ndarray,
    weights: np.ndarray,
    bias: float,
    target_sign: int,
    n_samples: int = 5,
    step: float = 0.05,
) -> list[Counterfactual]:
    """Generate counterfactuals for a linear score function.

    score = x·w + b, target_sign in {+1, -1}.
    """
    xv = np.asarray(x, dtype=float)
    w = np.asarray(weights, dtype=float)

    current = float(xv @ w + bias)
    if np.sign(current) == np.sign(target_sign):
        return [Counterfactual(features=xv.copy(), distance=0.0, target_score=current)]

    direction = np.sign(target_sign) * np.sign(w)
    cfs: list[Counterfactual] = []

    for i in range(n_samples):
        alpha = (i + 1) * step
        x_new = xv + alpha * direction
        score = float(x_new @ w + bias)
        dist = float(np.linalg.norm(x_new - xv))
        cfs.append(Counterfactual(features=x_new, distance=dist, target_score=score))

    cfs.sort(key=lambda cf: cf.distance)
    return cfs
