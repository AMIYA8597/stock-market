"""Batched TFT inference engine with attention extraction."""

from __future__ import annotations

import torch
from torch import Tensor

from research.models.tft.architecture import TemporalFusionTransformer


@torch.no_grad()
def tft_infer(
    model: TemporalFusionTransformer,
    x_hist: Tensor,
    x_fut: Tensor,
    device: str = "cpu",
) -> tuple[Tensor, Tensor]:
    r"""
    Run TFT inference in eval mode with deactivated gradients.

    **Computation:**

    1. Move model to device
    2. Set model.eval() to disable dropout and batch norm
    3. Forward pass: quantile predictions + attention weights
    4. Move results back to CPU for downstream processing

    **Args:**
        model: TemporalFusionTransformer instance (should be loaded from checkpoint).
        x_hist: Historical features (batch, seq_len, n_features, feature_dim).
        x_fut: Future features (batch, horizon, n_features, feature_dim).
        device: Compute device ('cpu' or 'cuda').

    **Returns:**
        q_pred: Quantile predictions (batch, horizon, n_quantiles) on CPU.
        attn_weights: Attention weights (batch, n_heads, horizon, seq_len) on CPU.
                     Visualizes which past timesteps influence each future prediction.

    **Example:**
        >>> model = TemporalFusionTransformer(n_features=5, feature_dim=8, horizon=21)
        >>> model.load_state_dict(torch.load('best_model.pt'))
        >>> x_h = torch.randn(32, 60, 5, 8)
        >>> x_f = torch.randn(32, 21, 5, 8)
        >>> pred, attn = tft_infer(model, x_h, x_f, device='cuda')
        >>> p10, p50, p90 = pred[..., 0], pred[..., 1], pred[..., 2]
        >>> print(f"P50 shape: {p50.shape}")  # (32, 21)
    """
    model = model.to(device)
    model.eval()

    # Ensure inputs are on correct device
    x_hist_dev = x_hist.to(device)
    x_fut_dev = x_fut.to(device)

    # Forward pass without gradient computation
    q_pred, attn_weights = model(x_hist_dev, x_fut_dev)

    # Return results on CPU for downstream processing
    return q_pred.cpu(), attn_weights.cpu()


class TFTInferenceEngine:
    r"""
    Production inference engine for TFT with batching and attention analysis.

    **Features:**
    - Batched inference with automatic device management
    - Attention weight extraction for interpretability
    - Variable importance scores from VSN weights
    - Efficient cached model loading

    **Example:**
        >>> engine = TFTInferenceEngine(model, device='cuda')
        >>> pred = engine.predict_single(x_h, x_f)  # Single sample
        >>> pred_batch = engine.batch_predict(x_h, x_f)  # Batch of samples
        >>> attn = engine.extract_attention_weights()
    """

    def __init__(
        self,
        model: TemporalFusionTransformer,
        device: str = "cpu",
    ) -> None:
        """Initialize inference engine with pre-trained model.

        Args:
            model: TemporalFusionTransformer instance (loaded from checkpoint).
            device: Compute device ('cpu' or 'cuda').
        """
        self.model = model
        self.device = device
        self._last_attention = None
        self._last_pred = None

    def predict_single(self, x_hist: Tensor, x_fut: Tensor) -> tuple[Tensor, Tensor]:
        r"""
        Single-sample inference.

        Args:
            x_hist: (1, seq_len, n_features, feature_dim).
            x_fut: (1, horizon, n_features, feature_dim).

        Returns:
            (q_pred, attn) where q_pred shape is (1, horizon, n_quantiles).
        """
        q_pred, attn = tft_infer(self.model, x_hist, x_fut, device=self.device)
        self._last_pred = q_pred
        self._last_attention = attn
        return q_pred, attn

    def batch_predict(self, x_hist: Tensor, x_fut: Tensor, max_batch: int = 128) -> tuple[Tensor, Tensor]:
        r"""
        Batched inference with memory-efficient chunking.

        Args:
            x_hist: (batch, seq_len, n_features, feature_dim).
            x_fut: (batch, horizon, n_features, feature_dim).
            max_batch: Maximum batch size per chunk (default 128).

        Returns:
            (q_pred, attn) with full batch size.
        """
        n = x_hist.shape[0]
        all_preds = []
        all_attns = []

        for start in range(0, n, max_batch):
            end = min(start + max_batch, n)
            q, a = tft_infer(
                self.model,
                x_hist[start:end],
                x_fut[start:end],
                device=self.device,
            )
            all_preds.append(q)
            all_attns.append(a)

        pred = torch.cat(all_preds, dim=0)
        attn = torch.cat(all_attns, dim=0)

        self._last_pred = pred
        self._last_attention = attn

        return pred, attn

    def extract_attention_weights(self) -> Tensor | None:
        r"""
        Extract attention weights from most recent inference.

        Returns attention weight tensor of shape:
        (batch, n_heads, horizon, seq_len)

        This visualizes which historical timesteps (columns) influence
        predictions at each future timestep (rows).

        Returns:
            Attention weights or None if no inference yet.
        """
        return self._last_attention

    def extract_variable_importance(self) -> Tensor | None:
        r"""
        Extract variable selection network (VSN) weights from model.

        VSN learns sparse per-feature importance: v = softmax(GRN(x)).

        **Note:** This would require modifying forward() to return VSN weights.
        Current implementation returns None; override to add VSN weight capture.

        Returns:
            VSN weights (batch, time, n_features) or None if not available.
        """
        # TODO: Capture VSN weights during forward pass
        return None

