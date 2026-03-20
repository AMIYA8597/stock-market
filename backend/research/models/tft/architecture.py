"""Temporal Fusion Transformer architecture implementation."""

from __future__ import annotations

import torch
from torch import Tensor, nn

from research.models.tft.components import GatedResidualNetwork, VariableSelectionNetwork


class TemporalFusionTransformer(nn.Module):
    """TFT with VSN, LSTM encoder/decoder, causal multi-head attention and quantile heads."""

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
        self.horizon = horizon
        self.quantiles = quantiles

        self.vsn = VariableSelectionNetwork(n_features=n_features, feature_dim=feature_dim, hidden_dim=hidden_dim)
        self.encoder = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.enc_skip = nn.Linear(hidden_dim, hidden_dim)
        self.dec_skip = nn.Linear(hidden_dim, hidden_dim)
        self.add_norm = nn.LayerNorm(hidden_dim)

        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)
        self.attn = nn.MultiheadAttention(hidden_dim, n_heads, batch_first=True)
        self.post_attn_grn = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim)

        self.quantile_head = nn.Linear(hidden_dim, len(quantiles))

    def _causal_mask(self, length: int, device: torch.device) -> Tensor:
        mask = torch.full((length, length), float("-inf"), device=device)
        return torch.triu(mask, diagonal=1)

    def forward(self, x_hist: Tensor, x_fut: Tensor) -> tuple[Tensor, Tensor]:
        """Args:
            x_hist: (batch, hist_len, n_features, feature_dim)
            x_fut: (batch, horizon, n_features, feature_dim)

        Returns:
            quantile_pred: (batch, horizon, n_quantiles)
            attention_weights: (batch, horizon, hist_len)
        """
        hist_sel, _ = self.vsn(x_hist)
        fut_sel, _ = self.vsn(x_fut)

        enc_out, (h, c) = self.encoder(hist_sel)
        enc_out = self.add_norm(enc_out + self.enc_skip(hist_sel))

        dec_out, _ = self.decoder(fut_sel, (h, c))
        dec_out = self.add_norm(dec_out + self.dec_skip(fut_sel))

        q = self.q_proj(dec_out)
        k = self.k_proj(enc_out)
        v = self.v_proj(enc_out)

        attn_out, attn_weights = self.attn(
            query=q,
            key=k,
            value=v,
            attn_mask=self._causal_mask(q.shape[1], q.device)[:, : k.shape[1]],
            need_weights=True,
        )

        fused = self.post_attn_grn(attn_out + dec_out)
        q_pred = self.quantile_head(fused)
        return q_pred, attn_weights
