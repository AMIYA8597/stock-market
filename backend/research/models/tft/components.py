"""Core TFT components: GRN, VSN and gated residual blocks."""

from __future__ import annotations

import torch
from torch import Tensor, nn


class GatedResidualNetwork(nn.Module):
    """Gated Residual Network used throughout TFT.

    eta1 = ELU(W1 x + Wc c + b1)
    eta2 = W2 eta1 + b2
    gate = sigmoid(W3 x + b3)
    out = LayerNorm(residual + gate * eta2)
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, context_dim: int | None = None, dropout: float = 0.1) -> None:
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.ctx = nn.Linear(context_dim, hidden_dim, bias=False) if context_dim is not None else None
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.gate = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(output_dim)
        self.residual_proj = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: Tensor, c: Tensor | None = None) -> Tensor:
        eta1 = self.fc1(x)
        if self.ctx is not None and c is not None:
            eta1 = eta1 + self.ctx(c)
        eta1 = self.dropout(torch.nn.functional.elu(eta1))
        eta2 = self.fc2(eta1)
        gate = torch.sigmoid(self.gate(x))
        residual = self.residual_proj(x)
        return self.norm(residual + gate * eta2)


class VariableSelectionNetwork(nn.Module):
    """Variable Selection Network for dynamic feature weighting."""

    def __init__(self, n_features: int, feature_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.n_features = n_features
        self.feature_dim = feature_dim
        self.selector_grn = GatedResidualNetwork(n_features * feature_dim, hidden_dim, n_features)
        self.feature_grns = nn.ModuleList(
            [GatedResidualNetwork(feature_dim, hidden_dim, hidden_dim) for _ in range(n_features)]
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        """Args:
            x: (batch, time, n_features, feature_dim)

        Returns:
            selected: (batch, time, hidden_dim)
            weights: (batch, time, n_features)
        """
        b, t, n, d = x.shape
        flat = x.reshape(b, t, n * d)
        weights = torch.softmax(self.selector_grn(flat), dim=-1)

        processed = []
        for i in range(self.n_features):
            processed.append(self.feature_grns[i](x[:, :, i, :]))
        stacked = torch.stack(processed, dim=2)
        selected = torch.sum(stacked * weights.unsqueeze(-1), dim=2)
        return selected, weights
