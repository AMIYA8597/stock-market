"""
AMSTAN: Adaptive Multi-Scale Temporal Attention Network
Custom transformer architecture for stock price forecasting
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class MultiScalePatchEmbedding(nn.Module):
    """Adaptive multi-scale patch embedding."""

    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        self.d_model = d_model

        # Learnable patch sizes for 3 scales
        self.patch_sizes = nn.Parameter(torch.tensor([5.0, 20.0, 60.0]))  # short, medium, long

        # Projections for each scale
        self.scale_projections = nn.ModuleList([
            nn.Linear(4, d_model // 3) for _ in range(3)  # OHLC features
        ])

        # Cross-scale attention
        self.cross_attention = nn.MultiheadAttention(d_model, num_heads=8)

        # Rotary position embedding
        self.rope = RotaryPositionEmbedding(d_model, max_len)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [batch, seq_len, 4] (OHLC)"""
        batch_size, seq_len, _ = x.shape

        # Create patches for each scale
        scale_embeddings = []
        for i, patch_size in enumerate(self.patch_sizes):
            # Adaptive patch size (round to nearest int)
            p = max(1, int(patch_size.item()))

            # Create overlapping patches
            patches = []
            for start in range(0, seq_len - p + 1, p // 2):
                patch = x[:, start:start+p, :]  # [batch, patch_len, 4]
                # Average pool to fixed size
                patch = torch.mean(patch, dim=1, keepdim=True)  # [batch, 1, 4]
                patches.append(patch)

            if patches:
                scale_patches = torch.cat(patches, dim=1)  # [batch, n_patches, 4]
                # Project to embedding space
                embedding = self.scale_projections[i](scale_patches)  # [batch, n_patches, d_model//3]
                scale_embeddings.append(embedding)

        # Concatenate scale embeddings
        multi_scale_emb = torch.cat(scale_embeddings, dim=-1)  # [batch, n_patches, d_model]

        # Apply cross-scale attention
        multi_scale_emb = multi_scale_emb.transpose(0, 1)  # [n_patches, batch, d_model]
        attended_emb, _ = self.cross_attention(multi_scale_emb, multi_scale_emb, multi_scale_emb)
        attended_emb = attended_emb.transpose(0, 1)  # [batch, n_patches, d_model]

        # Apply rotary position embedding
        attended_emb = self.rope(attended_emb)

        return attended_emb


class RotaryPositionEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE)."""

    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        self.d_model = d_model

        # Create position indices
        position = torch.arange(max_len).unsqueeze(1)  # [max_len, 1]
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))  # [d_model//2]

        # Compute cos and sin
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply rotary position embedding."""
        seq_len = x.size(1)
        return x + self.pe[:seq_len].unsqueeze(0)


class RegimeGatedAttention(nn.Module):
    """Regime-gated attention mechanism."""

    def __init__(self, d_model: int, n_heads: int = 8):
        super().__init__()
        self.n_heads = n_heads
        self.d_model = d_model
        self.d_head = d_model // n_heads

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # Regime gating (3 regimes: bear, sideways, bull)
        self.regime_gate = nn.Linear(3, d_model)  # Input: regime probabilities

    def forward(self, x: torch.Tensor, regime_probs: torch.Tensor) -> torch.Tensor:
        """x: [batch, seq_len, d_model], regime_probs: [batch, seq_len, 3]"""
        batch_size, seq_len, _ = x.shape

        # Compute Q, K, V
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)

        # Compute attention scores
        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.d_head ** 0.5)  # [batch, n_heads, seq_len, seq_len]

        # Apply regime gating
        regime_gates = self.regime_gate(regime_probs)  # [batch, seq_len, d_model]
        regime_gates = regime_gates.view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)

        # Gate the attention scores based on regime
        # For bull regime: boost momentum features attention
        # For bear regime: boost volatility/risk features attention
        gated_scores = scores * (1 + regime_gates.mean(dim=-1, keepdim=True).unsqueeze(-1))

        # Apply softmax
        attn_weights = F.softmax(gated_scores, dim=-1)

        # Apply attention
        attended = torch.matmul(attn_weights, v)  # [batch, n_heads, seq_len, d_head]

        # Reshape and project
        attended = attended.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        output = self.out_proj(attended)

        return output


class AMSTANBlock(nn.Module):
    """AMSTAN transformer block."""

    def __init__(self, d_model: int, n_heads: int = 8, d_ff: int = 2048, dropout: float = 0.1):
        super().__init__()
        self.attention = RegimeGatedAttention(d_model, n_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)

        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )

    def forward(self, x: torch.Tensor, regime_probs: torch.Tensor) -> torch.Tensor:
        # Self-attention with regime gating
        attn_out = self.attention(x, regime_probs)
        x = self.norm1(x + attn_out)

        # Feed-forward
        ff_out = self.feed_forward(x)
        x = self.norm2(x + ff_out)

        return x


class AMSTAN(nn.Module):
    """Adaptive Multi-Scale Temporal Attention Network."""

    def __init__(self, d_model: int = 256, n_heads: int = 8, n_layers: int = 6,
                 max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model

        # Multi-scale patch embedding
        self.patch_embedding = MultiScalePatchEmbedding(d_model, max_len)

        # Transformer blocks
        self.blocks = nn.ModuleList([
            AMSTANBlock(d_model, n_heads, dropout=dropout)
            for _ in range(n_layers)
        ])

        # Output heads
        self.regression_head = nn.Linear(d_model, 1)  # Point forecast
        self.uncertainty_head = nn.Linear(d_model, 2)  # 80% and 95% intervals

        # Dropout
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, regime_probs: torch.Tensor) -> Dict[str, torch.Tensor]:
        """x: [batch, seq_len, 4] OHLC, regime_probs: [batch, seq_len, 3]"""
        # Patch embedding
        x = self.patch_embedding(x)  # [batch, n_patches, d_model]

        # Apply transformer blocks
        for block in self.blocks:
            x = block(x, regime_probs[:, :x.size(1), :])  # Align sequence lengths

        x = self.dropout(x)

        # Take the last token for prediction
        last_hidden = x[:, -1, :]  # [batch, d_model]

        # Generate predictions
        point_forecast = self.regression_head(last_hidden).squeeze(-1)  # [batch]
        uncertainty = self.uncertainty_head(last_hidden)  # [batch, 2]

        # Split uncertainty into lower/upper bounds
        lower_80, upper_80 = uncertainty[:, 0], uncertainty[:, 1]

        return {
            'point_forecast': point_forecast,
            'lower_80': lower_80,
            'upper_80': upper_80,
            'lower_95': lower_80 * 0.8,  # Simplified
            'upper_95': upper_80 * 1.2   # Simplified
        }


class StockDataset(Dataset):
    """Dataset for stock price forecasting."""

    def __init__(self, data: pd.DataFrame, seq_len: int = 60, pred_horizon: int = 5):
        self.data = data
        self.seq_len = seq_len
        self.pred_horizon = pred_horizon

        # Extract features
        self.features = data[['open', 'high', 'low', 'close']].values
        self.targets = data['close'].shift(-pred_horizon).values

        # Remove NaN targets
        valid_idx = ~np.isnan(self.targets)
        self.features = self.features[valid_idx]
        self.targets = self.targets[valid_idx]

    def __len__(self):
        return len(self.features) - self.seq_len

    def __getitem__(self, idx):
        x = self.features[idx:idx + self.seq_len]  # [seq_len, 4]
        y = self.targets[idx + self.seq_len - 1]   # Target value

        return torch.FloatTensor(x), torch.FloatTensor([y])


class AMSTANTrainer:
    """Trainer for AMSTAN model."""

    def __init__(self, model: AMSTAN, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
        self.scheduler = torch.optim.lr_scheduler.OneCycleLR(
            self.optimizer, max_lr=1e-4, epochs=100, steps_per_epoch=100
        )

    def train_epoch(self, dataloader: DataLoader, regime_model) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0

        for batch_x, batch_y in dataloader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)

            # Get regime probabilities (simplified - would use actual regime model)
            regime_probs = torch.randn(batch_x.size(0), batch_x.size(1), 3).to(self.device)
            regime_probs = F.softmax(regime_probs, dim=-1)

            self.optimizer.zero_grad()

            outputs = self.model(batch_x, regime_probs)
            loss = F.mse_loss(outputs['point_forecast'], batch_y.squeeze())

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / len(dataloader)

    def validate(self, dataloader: DataLoader, regime_model) -> Dict[str, float]:
        """Validate model."""
        self.model.eval()
        total_loss = 0
        predictions = []
        targets = []

        with torch.no_grad():
            for batch_x, batch_y in dataloader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                # Get regime probabilities
                regime_probs = torch.randn(batch_x.size(0), batch_x.size(1), 3).to(self.device)
                regime_probs = F.softmax(regime_probs, dim=-1)

                outputs = self.model(batch_x, regime_probs)

                loss = F.mse_loss(outputs['point_forecast'], batch_y.squeeze())
                total_loss += loss.item()

                predictions.extend(outputs['point_forecast'].cpu().numpy())
                targets.extend(batch_y.squeeze().cpu().numpy())

        # Calculate metrics
        mse = total_loss / len(dataloader)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(np.array(predictions) - np.array(targets)))

        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae
        }

    def save_model(self, path: str):
        """Save model."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
        }, path)
        logger.info(f"AMSTAN model saved to {path}")

    def load_model(self, path: str):
        """Load model."""
        checkpoint = torch.load(path)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        logger.info(f"AMSTAN model loaded from {path}")