"""TFT dataset shaping utilities with strict windowing to prevent look-ahead bias."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor


@dataclass(slots=True)
class TimeSeriesDatasetConfig:
    """Configuration for TFT sliding window dataset construction.

    Attributes:
        seq_len: Length of historical input window (default 60 days).
        horizon: Length of future forecast window (default 21 days).
    """

    seq_len: int = 60
    horizon: int = 21


def build_tft_training_tensors(
    features: np.ndarray,
    target_returns: np.ndarray,
    cfg: TimeSeriesDatasetConfig,
) -> tuple[Tensor, Tensor, Tensor]:
    r"""
    Build TFT training windows with strict no-lookahead-bias windowing.

    **Prevents Look-Ahead Bias:**

    Window structure for each sample i:
    - x_hist[i]: features[i : i + seq_len]              [past 60 days]
    - x_fut[i]: features[i + seq_len : i + seq_len + horizon]  [future 21 days]
    - y[i]: target_returns[i + seq_len : i + seq_len + horizon] [next 21 days returns]

    No information from the future leaks into the history window.
    All samples use strictly past features and strictly future returns.

    **Args:**
        features: Feature tensor of shape (T, n_features, feature_dim).
            Example: T=300 days, n_features=5 (OHLCV), feature_dim=8 (embedding per feature).
        target_returns: Target return series of shape (T,) or (T, 1).
            Example: log-returns or next-day returns.
        cfg: TimeSeriesDatasetConfig with seq_len and horizon.

    **Returns:**
        x_hist: Historical features (N, seq_len, n_features, feature_dim).
        x_fut: Future features (N, horizon, n_features, feature_dim).
        y: Target returns (N, horizon).

        Where N = T - seq_len - horizon + 1 (number of sliding windows).

    **Raises:**
        ValueError: If features.ndim ≠ 3 or insufficient samples.

    **Example:**
        >>> # Simulate 1 year of daily data with 5 features (OHLCV)
        >>> features = np.random.randn(252, 5, 8)  # T=252, n_features=5, emb_dim=8
        >>> returns = np.random.randn(252)
        >>> x_h, x_f, y = build_tft_training_tensors(
        ...     features, returns, TimeSeriesDatasetConfig(seq_len=60, horizon=21)
        ... )
        >>> print(x_h.shape)  # (170, 60, 5, 8)  N=252-60-21+1=170
        >>> print(y.shape)    # (170, 21)
    """
    f = np.asarray(features, dtype=np.float32)
    y_src = np.asarray(target_returns, dtype=np.float32)

    # Validate input dimensions
    if f.ndim != 3:
        raise ValueError(f"features must be 3D (T, n_features, feature_dim), got shape {f.shape}")

    # Flatten 1D returns if needed
    if y_src.ndim == 1:
        y_src = y_src[:, None]

    t_total = f.shape[0]
    n_samples = t_total - cfg.seq_len - cfg.horizon + 1

    if n_samples <= 0:
        raise ValueError(
            f"Insufficient samples: T={t_total}, seq_len={cfg.seq_len}, "
            f"horizon={cfg.horizon} requires T ≥ {cfg.seq_len + cfg.horizon}"
        )

    x_hist = []
    x_fut = []
    y = []

    for i in range(n_samples):
        hist_start = i
        hist_end = i + cfg.seq_len
        fut_end = hist_end + cfg.horizon

        # Strict windowing: no lookahead
        x_hist.append(f[hist_start:hist_end])  # [t_i, ..., t_i + seq_len)
        x_fut.append(f[hist_end:fut_end])      # [t_i + seq_len, ..., t_i + seq_len + horizon)
        y.append(y_src[hist_end:fut_end, 0])   # Returns for future window

    return (
        torch.from_numpy(np.stack(x_hist)),
        torch.from_numpy(np.stack(x_fut)),
        torch.from_numpy(np.stack(y)),
    )


def normalize_features(features: np.ndarray, scaler: dict[str, np.ndarray] | None = None) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    r"""
    Normalize features using z-score (standardization) per feature dimension.

    **Normalization Formula:**
    x̃ = (x - μ) / σ

    where μ = mean and σ = std per feature (across time and batch).

    **Args:**
        features: Shape (T, n_features, feature_dim) or (batch, T, n_features, feature_dim).
        scaler: Optional pre-computed scaler dict with keys 'mean' and 'std'.
                If None, compute from features (for training).

    **Returns:**
        normalized_features: Same shape as input, z-score normalized.
        scaler: Dict with keys 'mean' and 'std' for inverse transformation.

    **Example:**
        >>> features = np.random.randn(252, 5, 8)
        >>> feat_norm, scaler = normalize_features(features)
        >>> # Later: apply same scaler to test data
        >>> test_norm, _ = normalize_features(test_features, scaler=scaler)
    """
    f = np.asarray(features, dtype=np.float32)
    original_shape = f.shape

    # Flatten to 2D: (T*batch, n_features*feature_dim)
    flat = f.reshape(-1, f.shape[-2] * f.shape[-1])

    if scaler is None:
        # Compute statistics during training
        mu = flat.mean(axis=0)
        sigma = flat.std(axis=0) + 1e-8  # Avoid division by zero
        scaler = {"mean": mu, "std": sigma}
    else:
        mu = scaler["mean"]
        sigma = scaler["std"]

    # Normalize
    normalized = (flat - mu) / sigma

    return normalized.reshape(original_shape).astype(np.float32), scaler

