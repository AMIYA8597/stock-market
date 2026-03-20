"""Training loop for Temporal Fusion Transformer."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from research.models.tft.architecture import TemporalFusionTransformer


@dataclass(slots=True)
class TFTTrainConfig:
    epochs: int = 20
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 64
    quantiles: tuple[float, float, float] = (0.1, 0.5, 0.9)


def _quantile_loss(y_true: Tensor, y_pred: Tensor, quantiles: tuple[float, ...]) -> Tensor:
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
    """Train TFT and return epoch loss trace."""
    model = model.to(device)
    optimizer = AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(cfg.epochs, 1))

    n = x_hist.shape[0]
    losses: list[float] = []

    for _ in range(cfg.epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, n, cfg.batch_size):
            end = min(start + cfg.batch_size, n)
            xh = x_hist[start:end].to(device)
            xf = x_fut[start:end].to(device)
            yt = y[start:end].to(device)

            optimizer.zero_grad(set_to_none=True)
            pred, _ = model(xh, xf)
            loss = _quantile_loss(yt, pred, cfg.quantiles)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += float(loss.item())
            n_batches += 1

        scheduler.step()
        losses.append(epoch_loss / max(n_batches, 1))

    return losses
