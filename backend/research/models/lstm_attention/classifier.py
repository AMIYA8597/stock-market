"""LSTM with Attention Classifier using PyTorch."""

from __future__ import annotations

import os
import pickle
import logging
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class AttentionLayer(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn_weights = nn.Parameter(torch.randn(hidden_dim, 1))

    def forward(self, lstm_out: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # lstm_out shape: [batch_size, seq_len, hidden_dim]
        # self.attn_weights shape: [hidden_dim, 1]
        scores = torch.matmul(lstm_out, self.attn_weights)  # [batch_size, seq_len, 1]
        attn_weights = torch.softmax(scores, dim=1)  # [batch_size, seq_len, 1]
        context = torch.sum(lstm_out * attn_weights, dim=1)  # [batch_size, hidden_dim]
        return context, attn_weights

class LSTMAttentionNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 32, num_layers: int = 1):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.attention = AttentionLayer(hidden_dim)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # x shape: [batch_size, seq_len, input_dim]
        lstm_out, _ = self.lstm(x)  # [batch_size, seq_len, hidden_dim]
        context, attn_weights = self.attention(lstm_out)
        out = self.sigmoid(self.fc(context))
        return out, attn_weights

class LSTMAttentionClassifier:
    """Estimator wrapping LSTMAttentionNet PyTorch model."""

    def __init__(self, seq_len: int = 10, epochs: int = 20, lr: float = 0.01):
        self.seq_len = seq_len
        self.epochs = epochs
        self.lr = lr
        self.model = None
        self.scaler = StandardScaler()
        self.features = [
            "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
            "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
            "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
            "dist_52w_high", "dist_52w_low", "drawdown",
            "range_pct", "close_to_open"
        ]

    def _create_sequences(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        X_seq, y_seq = [], []
        for i in range(len(X) - self.seq_len):
            X_seq.append(X[i:i+self.seq_len])
            y_seq.append(y[i+self.seq_len])
        return np.array(X_seq), np.array(y_seq)

    def fit(self, df: pd.DataFrame, y: pd.Series) -> LSTMAttentionClassifier:
        """Fit the scaler, prepare sequences, and train the model."""
        X_clean = df[self.features].dropna()
        y_clean = y.loc[X_clean.index].values
        X_scaled = self.scaler.fit_transform(X_clean)
        
        if len(X_scaled) <= self.seq_len:
            logger.warning("Insufficient samples to train LSTM")
            return self
            
        X_seq, y_seq = self._create_sequences(X_scaled, y_clean)
        
        X_tensor = torch.tensor(X_seq, dtype=torch.float32)
        y_tensor = torch.tensor(y_seq, dtype=torch.float32).unsqueeze(1)
        
        self.model = LSTMAttentionNet(input_dim=len(self.features))
        self.model.train()
        
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        
        for epoch in range(self.epochs):
            optimizer.zero_grad()
            outputs, _ = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            
        return self

    def predict_proba(self, df: pd.DataFrame) -> tuple[float, dict[str, float]]:
        """Predict directional probability and return attention weights."""
        if self.model is None:
            return 0.5, {}
            
        X_clean = df[self.features]
        X_scaled = self.scaler.transform(X_clean)
        
        if len(X_scaled) < self.seq_len:
            padding = np.zeros((self.seq_len - len(X_scaled), len(self.features)))
            X_scaled = np.vstack([padding, X_scaled])
        else:
            X_scaled = X_scaled[-self.seq_len:]
            
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).unsqueeze(0)
        
        self.model.eval()
        with torch.no_grad():
            prob, attn_weights = self.model(X_tensor)
            prob_val = float(prob.squeeze().item())
            attn_weights_val = attn_weights.squeeze().tolist()
            
        attn_dict = {f"t-{self.seq_len - 1 - i}": float(w) for i, w in enumerate(attn_weights_val)}
        return prob_val, attn_dict

    def save(self, path: Path | str) -> None:
        """Save model state dict and settings."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "scaler": self.scaler,
            "features": self.features,
            "seq_len": self.seq_len,
            "model_state_dict": self.model.state_dict() if self.model is not None else None
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path | str) -> LSTMAttentionClassifier | None:
        """Load model state and rebuild LSTMAttentionNet."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                state = pickle.load(f)
            inst = cls(seq_len=state["seq_len"])
            inst.scaler = state["scaler"]
            inst.features = state["features"]
            if state["model_state_dict"] is not None:
                inst.model = LSTMAttentionNet(input_dim=len(inst.features))
                inst.model.load_state_dict(state["model_state_dict"])
            return inst
        except Exception as e:
            logger.error(f"Failed to load LSTM model from {path}: {e}")
            return None
