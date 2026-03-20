"""Batched TFT inference helpers."""

from __future__ import annotations

import torch
from torch import Tensor

from research.models.tft.architecture import TemporalFusionTransformer


@torch.no_grad()
def tft_infer(model: TemporalFusionTransformer, x_hist: Tensor, x_fut: Tensor, device: str = "cpu") -> tuple[Tensor, Tensor]:
    """Run model inference and return quantiles plus attention map."""
    model = model.to(device)
    model.eval()
    q_pred, attn = model(x_hist.to(device), x_fut.to(device))
    return q_pred.cpu(), attn.cpu()
