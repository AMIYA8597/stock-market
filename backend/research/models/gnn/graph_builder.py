"""Graph construction from rolling asset return correlations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class CorrelationGraph:
    """Sparse directed graph representation used by the GNN."""

    adjacency: np.ndarray
    edge_index: np.ndarray
    edge_weight: np.ndarray
    symbols: list[str]


def build_correlation_graph(
    returns: np.ndarray,
    symbols: list[str],
    corr_threshold: float = 0.25,
    top_k: int = 8,
) -> CorrelationGraph:
    """Build graph using absolute pairwise correlation with threshold and top-k pruning.

    Args:
        returns: Matrix with shape (time, n_assets).
        symbols: Asset symbols matching n_assets.
    """
    r = np.asarray(returns, dtype=np.float64)
    if r.ndim != 2:
        raise ValueError("returns must be 2D (time, n_assets)")
    n_assets = r.shape[1]
    if len(symbols) != n_assets:
        raise ValueError("symbols length must match returns second dimension")

    corr = np.corrcoef(r, rowvar=False)
    corr = np.nan_to_num(corr)
    np.fill_diagonal(corr, 0.0)

    adjacency = np.zeros_like(corr)
    src: list[int] = []
    dst: list[int] = []
    w: list[float] = []

    for i in range(n_assets):
        row = np.abs(corr[i])
        valid_idx = np.where(row >= corr_threshold)[0]
        if valid_idx.size == 0:
            continue

        # Keep strongest top-k neighbors per node to cap graph density.
        sorted_idx = valid_idx[np.argsort(row[valid_idx])[::-1]]
        keep = sorted_idx[:top_k]
        for j in keep:
            weight = float(corr[i, j])
            adjacency[i, j] = weight
            src.append(i)
            dst.append(j)
            w.append(weight)

    if not src:
        edge_index = np.zeros((2, 0), dtype=np.int64)
        edge_weight = np.zeros((0,), dtype=np.float32)
    else:
        edge_index = np.array([src, dst], dtype=np.int64)
        edge_weight = np.array(w, dtype=np.float32)

    return CorrelationGraph(adjacency=adjacency.astype(np.float32), edge_index=edge_index, edge_weight=edge_weight, symbols=symbols)
