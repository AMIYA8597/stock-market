"""Dataset builders for dynamic graph snapshots."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class DynamicGraphSnapshot:
    """One temporal graph snapshot used by temporal GNN training."""

    returns_window: np.ndarray
    node_features: np.ndarray
    targets: np.ndarray
    symbols: list[str]


def build_dynamic_graph_dataset(
    returns: np.ndarray,
    features: np.ndarray,
    targets: np.ndarray,
    symbols: list[str],
    window: int = 60,
) -> list[DynamicGraphSnapshot]:
    """Create rolling graph snapshots.

    Args:
        returns: (time, n_assets) return matrix.
        features: (time, n_assets, n_features) feature cube.
        targets: (time, n_assets) labels.
        symbols: Ordered list of asset symbols.
        window: Rolling lookback window.
    """
    r = np.asarray(returns, dtype=np.float32)
    x = np.asarray(features, dtype=np.float32)
    y = np.asarray(targets, dtype=np.float32)

    if r.ndim != 2:
        raise ValueError("returns must be 2D")
    if x.ndim != 3:
        raise ValueError("features must be 3D")
    if y.ndim != 2:
        raise ValueError("targets must be 2D")
    if r.shape[0] != x.shape[0] or r.shape[0] != y.shape[0]:
        raise ValueError("returns/features/targets must share time dimension")

    out: list[DynamicGraphSnapshot] = []
    for t in range(window, r.shape[0]):
        out.append(
            DynamicGraphSnapshot(
                returns_window=r[t - window : t],
                node_features=x[t],
                targets=y[t],
                symbols=symbols,
            )
        )
    return out
