"""LSTM with Attention Classifier using PyTorch."""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_torch_cache = None

def _get_torch():
    global _torch_cache
    if _torch_cache is not None:
        return _torch_cache

    import torch
    import torch.nn as nn
    import torch.optim as optim
    
    torch.set_num_threads(1)
    
    class AttentionLayer(nn.Module):
        def __init__(self, hidden_dim: int):
            super().__init__()
            self.attn_weights = nn.Parameter(torch.randn(hidden_dim, 1))

        def forward(self, lstm_out: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            scores = torch.matmul(lstm_out, self.attn_weights)
            attn_weights = torch.softmax(scores, dim=1)
            context = torch.sum(lstm_out * attn_weights, dim=1)
            return context, attn_weights

    class LSTMAttentionNet(nn.Module):
        def __init__(self, input_dim: int, hidden_dim: int = 32, num_layers: int = 1, dropout: float = 0.5):
            super().__init__()
            self.lstm = nn.LSTM(
                input_dim,
                hidden_dim,
                num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0
            )
            self.attention = AttentionLayer(hidden_dim)
            self.dropout = nn.Dropout(dropout)
            self.fc = nn.Linear(hidden_dim, 1)
            self.sigmoid = nn.Sigmoid()

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            lstm_out, _ = self.lstm(x)
            context, attn_weights = self.attention(lstm_out)
            context = self.dropout(context)
            out = self.sigmoid(self.fc(context))
            return out, attn_weights

    _torch_cache = (torch, nn, optim, LSTMAttentionNet)
    return _torch_cache


class LSTMAttentionClassifier:
    """Estimator wrapping LSTMAttentionNet PyTorch model."""

    def __init__(self, seq_len: int = 10, epochs: int = 20, lr: float = 0.01):
        self.seq_len = seq_len
        self.epochs = epochs
        self.lr = lr
        self.model = None
        self.scaler = StandardScaler()
        self.features = []

    def _create_sequences(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        X_seq, y_seq = [], []
        for i in range(len(X) - self.seq_len):
            X_seq.append(X[i : i + self.seq_len])
            y_seq.append(y[i + self.seq_len])
        return np.array(X_seq), np.array(y_seq)

    def fit(self, df: pd.DataFrame, y: pd.Series) -> LSTMAttentionClassifier:
        """Fit the scaler, prepare sequences, and train the model with early stopping."""
        torch, nn, optim, LSTMAttentionNet = _get_torch()
        
        if not self.features:
            self.features = [c for c in df.select_dtypes(include=[np.number]).columns.tolist() if not c.startswith("target_")]

        X_clean = df[self.features].fillna(0)
        y_clean = y.loc[X_clean.index].values
        X_scaled = self.scaler.fit_transform(X_clean)

        if len(X_scaled) <= self.seq_len:
            logger.warning("Insufficient samples to train LSTM")
            return self

        X_seq, y_seq = self._create_sequences(X_scaled, y_clean)

        # 15% validation split for early stopping
        val_size = int(len(X_seq) * 0.15)
        if val_size == 0:
            val_size = 1

        train_size = len(X_seq) - val_size
        X_train, y_train = X_seq[:train_size], y_seq[:train_size]
        X_val, y_val = X_seq[train_size:], y_seq[train_size:]

        X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_train_tensor = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)

        X_val_tensor = torch.tensor(X_val, dtype=torch.float32)
        y_val_tensor = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)

        self.model = LSTMAttentionNet(input_dim=len(self.features))

        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-4)

        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        best_state = None

        for _epoch in range(self.epochs):
            self.model.train()
            optimizer.zero_grad()
            outputs, _ = self.model(X_train_tensor)
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()

            self.model.eval()
            with torch.no_grad():
                val_outputs, _ = self.model(X_val_tensor)
                val_loss = criterion(val_outputs, y_val_tensor).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = self.model.state_dict()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)

        return self

    def predict_proba(self, df: pd.DataFrame) -> tuple[float, dict[str, float]]:
        """Predict directional probability and return attention weights."""
        if self.model is None:
            return 0.5, {}

        torch, _, _, _ = _get_torch()

        X_clean = df[self.features]
        X_scaled = self.scaler.transform(X_clean)

        if len(X_scaled) < self.seq_len:
            padding = np.zeros((self.seq_len - len(X_scaled), len(self.features)))
            X_scaled = np.vstack([padding, X_scaled])
        else:
            X_scaled = X_scaled[-self.seq_len :]

        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).unsqueeze(0)

        self.model.eval()
        with torch.no_grad():
            prob, attn_weights = self.model(X_tensor)
            prob_val = float(prob.squeeze().item())
            attn_weights_val = attn_weights.squeeze().tolist()

        attn_dict = {f"t-{self.seq_len - 1 - i}": float(w) for i, w in enumerate(attn_weights_val)}
        return prob_val, attn_dict

    def predict_proba_batch(self, df: pd.DataFrame) -> pd.Series:
        if self.model is None:
            return pd.Series(0.5, index=df.index)

        torch, _, _, _ = _get_torch()

        X_clean = df[self.features].fillna(0)
        X_scaled = self.scaler.transform(X_clean)

        # Prepare sliding windows
        X_seq = []
        padded_X = np.vstack([np.zeros((self.seq_len - 1, len(self.features))), X_scaled])

        for i in range(len(X_scaled)):
            X_seq.append(padded_X[i: i + self.seq_len])

        X_tensor = torch.tensor(np.array(X_seq), dtype=torch.float32)

        self.model.eval()
        with torch.no_grad():
            probs, _ = self.model(X_tensor)
            probs = probs.squeeze().numpy()

        return pd.Series(probs, index=df.index)

    def save(self, path: Path | str) -> None:
        """Save model state dict and settings."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "scaler": self.scaler,
            "features": self.features,
            "seq_len": self.seq_len,
            "model_state_dict": self.model.state_dict() if self.model is not None else None,
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
                _, _, _, LSTMAttentionNet = _get_torch()
                inst.model = LSTMAttentionNet(input_dim=len(inst.features))
                inst.model.load_state_dict(state["model_state_dict"])
            return inst
        except Exception as e:
            logger.error(f"Failed to load LSTM model from {path}: {e}")
            return None
