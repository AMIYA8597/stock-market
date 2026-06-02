"""Training utilities for GraphSpilloverNet."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.optim import AdamW

from research.models.gnn.graph_builder import build_correlation_graph
from research.models.gnn.model import GraphSpilloverNet


@dataclass(slots=True)
class GNNTrainConfig:
    epochs: int = 50
    lr: float = 1e-3
    weight_decay: float = 1e-4
    corr_threshold: float = 0.25
    top_k: int = 8


def train_gnn(
    returns_window: np.ndarray,
    node_features: np.ndarray,
    targets: np.ndarray,
    symbols: list[str],
    cfg: GNNTrainConfig,
    device: str = "cpu",
) -> tuple[GraphSpilloverNet, list[float]]:
    """Train spillover model for one graph snapshot."""
    graph = build_correlation_graph(returns_window, symbols, cfg.corr_threshold, cfg.top_k)

    x = torch.as_tensor(node_features, dtype=torch.float32, device=device)
    y = torch.as_tensor(targets, dtype=torch.float32, device=device)
    edge_index = torch.as_tensor(graph.edge_index, dtype=torch.long, device=device)
    edge_weight = torch.as_tensor(graph.edge_weight, dtype=torch.float32, device=device)

    model = GraphSpilloverNet(input_dim=x.shape[1]).to(device)
    optimizer = AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    losses: list[float] = []

    for _ in range(cfg.epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        pred = model(x, edge_index, edge_weight)
        loss = torch.nn.functional.mse_loss(pred, y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    return model, losses
