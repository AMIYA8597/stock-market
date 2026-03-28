"""Core TFT components: GRN, VSN and gated residual blocks."""

from __future__ import annotations

import torch
from torch import Tensor, nn


class GateLinearUnit(nn.Module):
    r"""Gated Linear Unit (GLU) component.

    Implements the GLU activation: out = (W·x + b) ⊙ σ(V·x + c),
    where σ is the sigmoid function and ⊙ is element-wise multiplication.

    This is a simple gating mechanism that learns to selectively pass
    or suppress different dimensions of the input.

    Args:
        input_dim: Dimension of input features.
        output_dim: Dimension of output features.

    Example:
        >>> glu = GateLinearUnit(128, 64)
        >>> x = torch.randn(16, 128)  # batch_size=16, input_dim=128
        >>> y = glu(x)  # y.shape = (16, 64)
    """

    def __init__(self, input_dim: int, output_dim: int) -> None:
        super().__init__()
        self.fc_value = nn.Linear(input_dim, output_dim)
        self.fc_gate = nn.Linear(input_dim, output_dim)

    def forward(self, x: Tensor) -> Tensor:
        r"""
        Args:
            x: Input tensor of shape (..., input_dim)

        Returns:
            Gated output of shape (..., output_dim)
        """
        value = self.fc_value(x)
        gate = torch.sigmoid(self.fc_gate(x))
        return value * gate


class GatedResidualNetwork(nn.Module):
    r"""
    Gated Residual Network (GRN) component core to TFT.

    **Mathematical Formulation:**

    η₁ = ELU(W₁·x + W_c·c + b₁)    [if context c is provided]
    η₂ = W₂·η₁ + b₂
    gate = σ(W₃·x + b₃)             [σ = sigmoid]
    out = LayerNorm(x + gate ⊙ η₂)  [⊙ = element-wise multiplication]

    The gating mechanism learns to selectively pass or suppress different dimensions,
    allowing the network to learn which aspects of the context are relevant.
    The residual connection x enables gradient flow and helps train deep networks.

    **Args:**
        input_dim: Dimension of input features x.
        hidden_dim: Dimension of intermediate representation η₁.
        output_dim: Dimension of output features.
        context_dim: Optional dimension of external context c. If None, context is not used.
        dropout: Dropout rate applied after ELU (default 0.1).

    **Shape:**
        - Input x: (..., input_dim)
        - Input c (optional): (..., context_dim)
        - Output: (..., output_dim)

    **Example:**
        >>> grn = GatedResidualNetwork(input_dim=64, hidden_dim=128, output_dim=64)
        >>> x = torch.randn(32, 64)  # batch_size=32, input_dim=64
        >>> y = grn(x)  # y.shape = (32, 64)

        >>> grn_with_context = GatedResidualNetwork(
        ...     input_dim=64, hidden_dim=128, output_dim=64, context_dim=32
        ... )
        >>> c = torch.randn(32, 32)
        >>> y = grn_with_context(x, context=c)
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        context_dim: int | None = None,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # Dense layers
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.ctx = nn.Linear(context_dim, hidden_dim, bias=False) if context_dim is not None else None
        self.fc2 = nn.Linear(hidden_dim, output_dim)

        # Gate
        self.gate = nn.Linear(input_dim, output_dim)

        # Regularization
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(output_dim)

        # Residual projection (for dimension matching)
        self.residual_proj = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: Tensor, c: Tensor | None = None) -> Tensor:
        r"""
        Forward pass.

        Args:
            x: Input tensor of shape (..., input_dim).
            c: Optional context tensor of shape (..., context_dim).

        Returns:
            Output tensor of shape (..., output_dim).
        """
        # Dense path: ELU activation with context addition
        eta1 = self.fc1(x)
        if self.ctx is not None and c is not None:
            c_proj = self.ctx(c)
            eta1 = eta1 + c_proj
        eta1 = self.dropout(torch.nn.functional.elu(eta1))

        # Dense output
        eta2 = self.fc2(eta1)

        # Gating mechanism: learned gate controlling information flow
        gate = torch.sigmoid(self.gate(x))

        # Residual connection with gating
        residual = self.residual_proj(x)
        out = residual + gate * eta2

        # Layer normalization
        return self.norm(out)


class VariableSelectionNetwork(nn.Module):
    r"""
    Variable Selection Network (VSN) for sparse feature importance learning.

    **Mathematical Formulation:**

    Given K input features at one timestep: [x₁, x₂, ..., xₖ]

    1. Feature selection (sparse weights):
       ξ = concat(x₁, x₂, ..., xₖ)         [flatten all features]
       v = softmax(GRN(ξ))                  [K-dim selection weights, Σvₖ = 1]

    2. Per-feature processing:
       x̃ₖ = GRN(xₖ)                        [independent GRN per feature]

    3. Weighted aggregation:
       X̃ = Σₖ vₖ ⊙ x̃ₖ                     [weighted sum with sparse weights]

    The VSN learns which features are important at each timestep, providing
    interpretability (which inputs matter?) and adaptive feature engineering.

    **Args:**
        n_features: Number of input features K (e.g., OHLCV = 5, with technicals = 40).
        feature_dim: Dimension of each feature embedding d (e.g., 8).
        hidden_dim: Hidden dimension of internal GRNs (e.g., 64).

    **Shape:**
        - Input x: (batch, time, n_features, feature_dim)
        - Output selected: (batch, time, hidden_dim)
        - Output weights: (batch, time, n_features)

    **Example:**
        >>> vsn = VariableSelectionNetwork(n_features=5, feature_dim=8, hidden_dim=64)
        >>> x = torch.randn(32, 60, 5, 8)  # batch, time, n_features, feature_dim
        >>> selected, weights = vsn(x)
        >>> print(selected.shape)  # (32, 60, 64)
        >>> print(weights.shape)   # (32, 60, 5)
        >>> print(f"Feature importance: {weights[0, -1]}") # latest timestep weights
    """

    def __init__(self, n_features: int, feature_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.n_features = n_features
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim

        # GRN for learning sparse feature selection weights
        self.selector_grn = GatedResidualNetwork(
            input_dim=n_features * feature_dim,
            hidden_dim=hidden_dim,
            output_dim=n_features,
        )

        # Independent GRN for each feature's embedded representation
        self.feature_grns = nn.ModuleList(
            [
                GatedResidualNetwork(
                    input_dim=feature_dim,
                    hidden_dim=hidden_dim,
                    output_dim=hidden_dim,
                )
                for _ in range(n_features)
            ]
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        r"""
        Forward pass: learn sparse feature weights and aggregate selected features.

        Args:
            x: Input tensor of shape (batch, time, n_features, feature_dim).

        Returns:
            selected: Weighted feature aggregation (batch, time, hidden_dim).
            weights: Learned feature importance (batch, time, n_features), sum to 1 per timestep.

        Example:
            >>> batch_size, seq_len, n_feat, feat_dim = 32, 60, 5, 8
            >>> x = torch.randn(batch_size, seq_len, n_feat, feat_dim)
            >>> selected, weights = vsn(x)
            >>> assert selected.shape == (batch_size, seq_len, hidden_dim)
            >>> assert weights.shape[-1] == n_feat
            >>> assert torch.allclose(weights.sum(dim=-1), torch.ones(batch_size, seq_len))
        """
        batch_size, time_steps, n_features, feature_dim = x.shape

        # Flatten features: combine all feature dimensions
        x_flat = x.reshape(batch_size, time_steps, n_features * feature_dim)

        # Learn sparse selection weights via softmax gating
        weights = torch.softmax(self.selector_grn(x_flat), dim=-1)  # (batch, time, n_features)

        # Process each feature independently through its GRN
        processed_features = []
        for i in range(n_features):
            # Extract feature i across all timesteps: (batch, time, feature_dim)
            feat_i = x[:, :, i, :]
            # Process through feature-specific GRN: (batch, time, hidden_dim)
            processed = self.feature_grns[i](feat_i)
            processed_features.append(processed)

        # Stack all processed features: (batch, time, n_features, hidden_dim)
        stacked = torch.stack(processed_features, dim=2)

        # Weighted aggregation: multiply by sparse weights and sum
        # weights: (batch, time, n_features, 1), stacked: (batch, time, n_features, hidden_dim)
        weighted = stacked * weights.unsqueeze(-1)
        selected = weighted.sum(dim=2)  # (batch, time, hidden_dim)

        return selected, weights

