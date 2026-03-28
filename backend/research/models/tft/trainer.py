"""Training loop for Temporal Fusion Transformer with quantile loss."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from research.models.tft.architecture import TemporalFusionTransformer


@dataclass(slots=True)
class TFTTrainConfig:
    """Configuration for TFT training.

    Attributes:
        epochs: Number of training epochs (default 20).
        lr: Learning rate for AdamW optimizer (default 1e-3).
        weight_decay: L2 regularization coefficient (default 1e-4).
        batch_size: Batch size for training (default 64).
        quantiles: Quantile levels for regression (default (0.1, 0.5, 0.9)).
    """

    epochs: int = 20
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 64
    quantiles: tuple[float, float, float] = (0.1, 0.5, 0.9)


def _quantile_loss(y_true: Tensor, y_pred: Tensor, quantiles: tuple[float, ...]) -> Tensor:
    r"""
    Compute pinball (quantile) loss for all quantiles.

    QL = Σ_q Σ_t [q·max(y_t - ŷ_{q,t}, 0) + (1-q)·max(ŷ_{q,t} - y_t, 0)]

    Args:
        y_true: Observed values (batch, horizon).
        y_pred: Quantile predictions (batch, horizon, n_quantiles).
        quantiles: Tuple of quantile levels.

    Returns:
        Scalar loss tensor averaged over all quantiles and samples.
    """
    losses = []
    for i, q in enumerate(quantiles):
        err = y_true - y_pred[..., i]
        losses.append(torch.maximum(q * err, (q - 1.0) * err))
    stacked = torch.stack(losses, dim=-1)
    return stacked.mean()


def train_tft(
    model: TemporalFusionTransformer,
    x_hist: Tensor,
    x_fut: Tensor,
    y: Tensor,
    cfg: TFTTrainConfig,
    device: str = "cpu",
) -> list[float]:
    r"""
    Train TFT model with quantile loss, cosine annealing scheduler, and gradient clipping.

    **Training Configuration:**

    1. Optimizer: AdamW with L2 regularization
       - Learning rate: cfg.lr (default 1e-3)
       - Weight decay: cfg.weight_decay (default 1e-4)

    2. Learning Rate Scheduler: CosineAnnealingLR
       - Anneals learning rate from lr to 0 over epochs
       - lr(t) = lr · (1 + cos(πt/T_max)) / 2

    3. Gradient Clipping: max_norm=1.0 to stabilize training

    4. Loss Function: Quantile (pinball) loss
       QL = Σ_q Σ_t [q·max(y-ŷ_q, 0) + (1-q)·max(ŷ_q-y, 0)]
       This encourages calibrated uncertainty estimates (P10, P50, P90).

    **Args:**
        model: TemporalFusionTransformer instance.
        x_hist: Historical features (N, seq_len, n_features, feature_dim).
        x_fut: Future features (N, horizon, n_features, feature_dim).
        y: Target returns (N, horizon).
        cfg: TFTTrainConfig with hyperparameters.
        device: 'cpu' or 'cuda' (default 'cpu').

    **Returns:**
        losses: List of average epoch losses, length = cfg.epochs.

    **Example:**
        >>> model = TemporalFusionTransformer(n_features=5, feature_dim=8, horizon=21)
        >>> x_h = torch.randn(1000, 60, 5, 8)
        >>> x_f = torch.randn(1000, 21, 5, 8)
        >>> y = torch.randn(1000, 21)
        >>> cfg = TFTTrainConfig(epochs=20, lr=1e-3, batch_size=64)
        >>> loss_trace = train_tft(model, x_h, x_f, y, cfg, device='cuda')
        >>> print(f"Final loss: {loss_trace[-1]:.4f}")
    """
    model = model.to(device)
    optimizer = AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(cfg.epochs, 1))

    n = x_hist.shape[0]
    losses: list[float] = []

    for epoch in range(cfg.epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        # Shuffle data for better generalization
        perm = torch.randperm(n, device=device if device.startswith("cuda") else torch.device("cpu"))
        if device.startswith("cuda"):
            perm = perm.to(device)

        for start in range(0, n, cfg.batch_size):
            end = min(start + cfg.batch_size, n)
            batch_idx = perm[start:end]

            xh = x_hist[batch_idx].to(device)
            xf = x_fut[batch_idx].to(device)
            yt = y[batch_idx].to(device)

            # Forward pass
            optimizer.zero_grad(set_to_none=True)
            pred, _ = model(xh, xf)

            # Compute loss
            loss = _quantile_loss(yt, pred, cfg.quantiles)

            # Backward pass with gradient clipping
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += float(loss.item())
            n_batches += 1

        # Step scheduler
        scheduler.step()

        avg_loss = epoch_loss / max(n_batches, 1)
        losses.append(avg_loss)

        if (epoch + 1) % max(1, cfg.epochs // 10) == 0:
            print(f"Epoch {epoch+1}/{cfg.epochs}, Loss: {avg_loss:.6f}, LR: {scheduler.get_last_lr()[0]:.6e}")

    return losses

