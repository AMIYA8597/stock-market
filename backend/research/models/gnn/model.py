"""Lightweight graph attention-style message passing network."""

from __future__ import annotations

import torch
from torch import Tensor, nn


class GraphSpilloverNet(nn.Module):
    """Simple two-layer message passing model with learned edge attention."""

    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 1) -> None:
        super().__init__()
        self.node_proj = nn.Linear(input_dim, hidden_dim)
        self.attn_src = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.attn_dst = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.msg_proj = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim),
        )

    def _propagate(self, h: Tensor, edge_index: Tensor, edge_weight: Tensor) -> Tensor:
        n = h.shape[0]
        src = edge_index[0]
        dst = edge_index[1]

        h_src = h[src]
        h_dst = h[dst]
        attn_logits = (self.attn_src(h_src) * self.attn_dst(h_dst)).sum(dim=-1)
        attn_logits = attn_logits * edge_weight

        alpha = torch.zeros_like(attn_logits)
        for node in torch.unique(dst):
            mask = dst == node
            alpha[mask] = torch.softmax(attn_logits[mask], dim=0)

        msg = self.msg_proj(h_src) * alpha.unsqueeze(-1)
        agg = torch.zeros((n, h.shape[1]), device=h.device, dtype=h.dtype)
        agg.index_add_(0, dst, msg)
        return self.norm(h + agg)

    def forward(self, node_features: Tensor, edge_index: Tensor, edge_weight: Tensor) -> Tensor:
        """Args:
            node_features: (n_nodes, input_dim)
            edge_index: (2, n_edges)
            edge_weight: (n_edges,)
        """
        h = torch.relu(self.node_proj(node_features))
        if edge_index.numel() > 0:
            h = self._propagate(h, edge_index, edge_weight)
        return self.head(h).squeeze(-1)
