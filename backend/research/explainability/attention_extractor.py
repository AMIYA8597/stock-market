"""Attention weight extraction helpers for sequence models."""

from __future__ import annotations

import numpy as np
import torch
from torch import Tensor


@torch.no_grad()
def extract_attention_weights(attention_tensor: Tensor) -> np.ndarray:
    """Convert attention tensor to CPU numpy with shape normalization."""
    attn = attention_tensor.detach().cpu().numpy()
    if attn.ndim == 4:
        # (batch, heads, tgt, src) -> mean over batch
        return attn.mean(axis=0)
    if attn.ndim == 3:
        # (batch, tgt, src) -> mean over batch
        return attn.mean(axis=0, keepdims=True)
    return np.asarray(attn)


def summarize_attention(attn: np.ndarray, top_k: int = 5) -> dict[str, list[float] | list[int]]:
    """Return mean timestep importance and top timestep indices."""
    a = np.asarray(attn, dtype=float)
    if a.ndim == 3:
        # heads x tgt x src -> average over heads and target positions
        mean_weights = a.mean(axis=(0, 1))
    elif a.ndim == 2:
        mean_weights = a.mean(axis=0)
    else:
        mean_weights = a.reshape(-1)

    top_idx = np.argsort(mean_weights)[::-1][:top_k]
    return {
        "mean_weights": mean_weights.tolist(),
        "top_indices": top_idx.astype(int).tolist(),
    }
