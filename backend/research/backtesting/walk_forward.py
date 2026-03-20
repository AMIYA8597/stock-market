"""Combinatorial Purged Cross Validation (CPCV) utilities."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable

import numpy as np


@dataclass(slots=True)
class CPCVSplit:
    train_idx: np.ndarray
    test_idx: np.ndarray


def generate_cpcv_splits(n_samples: int, n_splits: int, purge_days: int, embargo_days: int) -> list[CPCVSplit]:
    """Generate CPCV splits using all C(k, 2) fold-pair test combinations."""
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")

    fold_bounds = np.linspace(0, n_samples, n_splits + 1, dtype=int)
    fold_indices = [np.arange(fold_bounds[i], fold_bounds[i + 1]) for i in range(n_splits)]

    splits: list[CPCVSplit] = []
    for i, j in combinations(range(n_splits), 2):
        test_idx = np.concatenate([fold_indices[i], fold_indices[j]])

        mask = np.ones(n_samples, dtype=bool)
        mask[test_idx] = False

        for idx in test_idx:
            lo = max(0, idx - purge_days)
            hi = min(n_samples, idx + embargo_days + 1)
            mask[lo:hi] = False

        train_idx = np.where(mask)[0]
        splits.append(CPCVSplit(train_idx=train_idx, test_idx=np.sort(test_idx)))

    return splits


def evaluate_cpcv(
    returns: np.ndarray,
    n_splits: int,
    purge_days: int,
    embargo_days: int,
    scorer: Callable[[np.ndarray], float],
) -> np.ndarray:
    """Compute score distribution across CPCV splits using provided scorer."""
    r = np.asarray(returns, dtype=float)
    scores = []
    for split in generate_cpcv_splits(len(r), n_splits, purge_days, embargo_days):
        scores.append(float(scorer(r[split.test_idx])))
    return np.asarray(scores, dtype=float)
