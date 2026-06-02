"""Temporal Fusion Transformer architecture implementation."""

from __future__ import annotations

import torch
from torch import Tensor, nn

from research.models.tft.components import GatedResidualNetwork, VariableSelectionNetwork


class TemporalFusionTransformer(nn.Module):
    r"""
    Temporal Fusion Transformer for multi-horizon quantile forecasting.

    **Architecture Overview:**

    The TFT combines several components:
    1. Variable Selection Network (VSN): Learns sparse feature importance
       v = softmax(GRN(concat(x₁,...,xₖ)))  [K-dim selection weights]
       x̃ = Σₖ vₖ · GRN(xₖ)                  [weighted feature combination]

    2. LSTM Encoder-Decoder:
       - Encoder: LSTM over past T_hist timesteps → hidden state h, cell c
       - Decoder: LSTM over future horizon T_fut using (h, c) → embeddings
       - Gated Skip Connections: out = LayerNorm(LSTM_out + Linear(x))

    3. Temporal Self-Attention (causal):
       Q = Wq·h_dec,  K = Wk·h_enc,  V = Wv·h_enc
       A(Q,K,V) = softmax(QKᵀ/√d_k + causal_mask) · V
       Multi-head: 8 parallel heads concatenated and projected

    4. Quantile Regression Heads:
       For each q ∈ {0.1, 0.5, 0.9}:
           ŷ_q(t) = Wq·(attention_out + h_dec)
       Loss: QL = Σ_q Σ_t [q·max(y-ŷ_q, 0) + (1-q)·max(ŷ_q-y, 0)]

    **Args:**
        n_features: Number of input features (e.g., OHLCV + technicals = ~40)
        feature_dim: Embedding dimension per feature
        hidden_dim: Hidden state dimension for LSTM and attention (default 64)
        n_heads: Number of attention heads (default 8)
        horizon: Forecast horizon in days (e.g., 21 = 1 month ahead)
        quantiles: Regression quantiles as tuple (default (0.1, 0.5, 0.9) for P10, P50, P90)

    **Attributes:**
        vsn: VariableSelectionNetwork for feature selection
        encoder: LSTM encoder
        decoder: LSTM decoder
        enc_skip: Gated skip connection for encoder
        dec_skip: Gated skip connection for decoder
        add_norm: LayerNorm for skip connections
        q_proj, k_proj, v_proj: Projections for multi-head attention
        attn: MultiheadAttention module with causal masking
        post_attn_grn: GRN after attention fusion
        quantile_head: Linear output layer → num_quantiles

    **Example:**
        >>> model = TemporalFusionTransformer(
        ...     n_features=5,      # OHLCV
        ...     feature_dim=8,      # Per-feature embedding
        ...     hidden_dim=64,
        ...     horizon=21,
        ... )
        >>> x_hist = torch.randn(32, 60, 5, 8)  # batch, past 60 days, 5 features, 8-dim each
        >>> x_fut = torch.randn(32, 21, 5, 8)   # batch, future 21 days, 5 features, 8-dim each
        >>> pred, attn = model(x_hist, x_fut)   # (32, 21, 3), (32, 21, 60)
    """

    def __init__(
        self,
        n_features: int,
        feature_dim: int,
        hidden_dim: int = 64,
        n_heads: int = 8,
        horizon: int = 21,
        quantiles: tuple[float, float, float] = (0.1, 0.5, 0.9),
    ) -> None:
        super().__init__()
        if hidden_dim % n_heads != 0:
            raise ValueError(f"hidden_dim ({hidden_dim}) must be divisible by n_heads ({n_heads})")

        self.n_features = n_features
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim
        self.n_heads = n_heads
        self.horizon = horizon
        self.quantiles = quantiles

        # Feature selection
        self.vsn = VariableSelectionNetwork(
            n_features=n_features,
            feature_dim=feature_dim,
            hidden_dim=hidden_dim,
        )

        # Encoder-Decoder
        self.encoder = nn.LSTM(hidden_dim, hidden_dim, batch_first=True, num_layers=1)
        self.decoder = nn.LSTM(hidden_dim, hidden_dim, batch_first=True, num_layers=1)
        self.enc_skip = nn.Linear(hidden_dim, hidden_dim)
        self.dec_skip = nn.Linear(hidden_dim, hidden_dim)
        self.ln_skip = nn.LayerNorm(hidden_dim)

        # Attention
        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)
        self.attn = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=n_heads,
            batch_first=True,
            dropout=0.1,
        )
        self.post_attn_grn = GatedResidualNetwork(
            input_dim=hidden_dim,
            hidden_dim=hidden_dim,
            output_dim=hidden_dim,
        )

        # Output heads
        self.quantile_head = nn.Linear(hidden_dim, len(quantiles))

        # Initialization
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize parameters with Xavier uniform for linear layers, orthogonal for RNNs."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LSTM):
                for name, param in m.named_parameters():
                    if "weight_ih" in name:
                        nn.init.xavier_uniform_(param)
                    elif "weight_hh" in name:
                        nn.init.orthogonal_(param)
                    elif "bias" in name:
                        nn.init.zeros_(param)

    def _causal_mask(self, length: int, device: torch.device) -> Tensor:
        """
        Create a causal attention mask: upper triangle (future tokens) → -∞.

        Args:
            length: Sequence length.
            device: Target device.

        Returns:
            Causal mask of shape (length, length).
        """
        mask = torch.full((length, length), float("-inf"), device=device)
        return torch.triu(mask, diagonal=1)

    def forward(self, x_hist: Tensor, x_fut: Tensor) -> tuple[Tensor, Tensor]:
        r"""
        Forward pass: encode past → decode future with attention.

        **Computation Flow:**
        1. VSN Feature Selection:
           hist_sel = VSN(x_hist)  [batch, T_hist, hidden_dim]
           fut_sel = VSN(x_fut)    [batch, T_fut, hidden_dim]

        2. LSTM Encoder:
           enc_out, (h, c) = LSTM_enc(hist_sel)
           enc_out = LayerNorm(enc_out + skip(hist_sel))

        3. LSTM Decoder (initialized with encoder final states):
           dec_out, _ = LSTM_dec(fut_sel, (h, c))
           dec_out = LayerNorm(dec_out + skip(fut_sel))

        4. Multi-Head Attention:
           Q = Wq(dec_out),  K = Wk(enc_out),  V = Wv(enc_out)
           attn_out = MultiHeadAttn(Q, K, V, mask=causal_mask)

        5. Quantile Output:
           fused = GRN(attn_out + dec_out)
           pred = Linear(fused)  [batch, horizon, n_quantiles]

        Args:
            x_hist: Historical input of shape (batch, T_hist, n_features, feature_dim)
                Usually T_hist = 60 (past 60 days).
            x_fut: Future input of shape (batch, T_fut, n_features, feature_dim)
                Usually T_fut = horizon = 21 (next 21 days).

        Returns:
            quantile_pred: Quantile predictions (batch, horizon, n_quantiles)
                Each quantile ∈ (0, 1) for P10, P50, P90 respectively.
            attention_weights: Attention weights (batch, n_heads, T_fut, T_hist)
                Visualizes which historical timesteps influence each future prediction.

        Example:
            >>> model = TemporalFusionTransformer(n_features=5, feature_dim=8, horizon=21)
            >>> x_h = torch.randn(32, 60, 5, 8)
            >>> x_f = torch.randn(32, 21, 5, 8)
            >>> pred, attn_w = model(x_h, x_f)
            >>> p10, p50, p90 = pred[..., 0], pred[..., 1], pred[..., 2]
        """
        x_hist.shape[0]

        # 1. Variable selection
        hist_sel, _ = self.vsn(x_hist)  # (batch, T_hist, hidden_dim)
        fut_sel, _ = self.vsn(x_fut)    # (batch, T_fut, hidden_dim)

        # 2. LSTM encoder
        enc_out, (h, c) = self.encoder(hist_sel)
        enc_out = self.ln_skip(enc_out + self.enc_skip(hist_sel))

        # 3. LSTM decoder (initialized with encoder final state)
        dec_out, _ = self.decoder(fut_sel, (h, c))
        dec_out = self.ln_skip(dec_out + self.dec_skip(fut_sel))

        # 4. Multi-head self-attention
        q = self.q_proj(dec_out)  # (batch, T_fut, hidden_dim)
        k = self.k_proj(enc_out)  # (batch, T_hist, hidden_dim)
        v = self.v_proj(enc_out)  # (batch, T_hist, hidden_dim)

        attn_out, attn_weights = self.attn(
            query=q,
            key=k,
            value=v,
            attn_mask=self._causal_mask(q.shape[1], q.device)[:, : k.shape[1]],
            need_weights=True,
        )

        # 5. Quantile output
        fused = self.post_attn_grn(attn_out + dec_out)
        q_pred = self.quantile_head(fused)  # (batch, horizon, n_quantiles)

        return q_pred, attn_weights

