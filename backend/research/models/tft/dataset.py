"""TFT dataset shaping utilities with strict windowing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor


@dataclass(slots=True)
class TimeSeriesDatasetConfig:
    seq_len: int = 60
    horizon: int = 21


def build_tft_training_tensors(features: np.ndarray, target_returns: np.ndarray, cfg: TimeSeriesDatasetConfig) -> tuple[Tensor, Tensor, Tensor]:
    """Build TFT sliding windows.

    Args:
        features: (T, n_features, feature_dim)
        target_returns: (T, horizon) or (T,)

    Returns:
        x_hist: (N, seq_len, n_features, feature_dim)
        x_fut: (N, horizon, n_features, feature_dim)
        y: (N, horizon)
    """
    f = np.asarray(features, dtype=np.float32)
    y_src = np.asarray(target_returns, dtype=np.float32)
    if y_src.ndim == 1:
        y_src = y_src[:, None]

    t_total = f.shape[0]
    n_samples = t_total - cfg.seq_len - cfg.horizon + 1
    if n_samples <= 0:
        raise ValueError("Insufficient samples for configured seq_len and horizon")

    x_hist = []
    x_fut = []
    y = []
    for i in range(n_samples):
        hist_start = i
        hist_end = i + cfg.seq_len
        fut_end = hist_end + cfg.horizon

        x_hist.append(f[hist_start:hist_end])
        x_fut.append(f[hist_end:fut_end])
        y.append(y_src[hist_end:fut_end, 0])

    return (
        torch.from_numpy(np.stack(x_hist)),
        torch.from_numpy(np.stack(x_fut)),
        torch.from_numpy(np.stack(y)),
    )
