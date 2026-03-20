"""Inference helpers for cross-asset spillover predictions."""

from __future__ import annotations

import numpy as np
import torch

from research.models.gnn.graph_builder import build_correlation_graph
from research.models.gnn.model import GraphSpilloverNet


def infer_spillover(
    model: GraphSpilloverNet,
    returns_window: np.ndarray,
    node_features: np.ndarray,
    symbols: list[str],
    corr_threshold: float = 0.25,
    top_k: int = 8,
    device: str = "cpu",
) -> dict[str, float]:
    """Run one-shot spillover inference over the correlation graph."""
    graph = build_correlation_graph(returns_window, symbols, corr_threshold, top_k)
    x = torch.as_tensor(node_features, dtype=torch.float32, device=device)
    edge_index = torch.as_tensor(graph.edge_index, dtype=torch.long, device=device)
    edge_weight = torch.as_tensor(graph.edge_weight, dtype=torch.float32, device=device)

    model = model.to(device)
    model.eval()
    with torch.no_grad():
        pred = model(x, edge_index, edge_weight).detach().cpu().numpy()

    return {sym: float(val) for sym, val in zip(symbols, pred, strict=True)}
