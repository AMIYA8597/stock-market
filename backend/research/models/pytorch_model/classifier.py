"""LSTM Walk-Forward Directional Classifier (Optional Phase A4 model)."""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FeatureMismatchError(ValueError):
    """Raised when features needed for the model prediction are missing in input."""

    def __init__(self, missing_features: list[str]):
        self.missing_features = missing_features
        super().__init__(f"model unavailable: missing features {missing_features}")


class LSTMDirectionalClassifier:
    """LSTM classifier predicting directional price movement.

    Uses PyTorch. Imports lazily to avoid heavy overhead.
    Designed for Walk-Forward pipeline evaluation.
    """

    def __init__(
        self,
        window_size: int = 5,
        hidden_size: int = 16,
        num_layers: int = 1,
        dropout: float = 0.3,
        lr: float = 0.005,
        epochs: int = 50,
        batch_size: int = 32,
    ):
        self.window_size = window_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size

        self.scaler = StandardScaler()
        self.model_state_dict = None  # To persist model weights

        self.features = [
            "ret_1d",
            "ret_5d",
            "ret_21d",
            "momentum_63d",
            "RSI_14",
            "MACDh_12_26_9",
            "BBP_20_2.0",
            "ATRr_14",
            "ADX_14",
            "realized_vol_21d",
            "yang_zhang_vol_21d",
            "dist_52w_high",
            "dist_52w_low",
            "drawdown",
            "range_pct",
            "close_to_open",
            "sentiment_score",
            "news_volume",
            "sentiment_pos_neg_ratio",
            "market_sentiment_index",
            "sentiment_momentum_3d",
            "regime_state",
            "garch_vol",
        ]

    def _create_dataset(self, X: np.ndarray, y: np.ndarray | None = None) -> tuple:
        """Create rolling windows of shape (N - window_size + 1, window_size, features)."""
        Xs = []
        ys = []
        for i in range(len(X) - self.window_size + 1):
            Xs.append(X[i : i + self.window_size])
            if y is not None:
                ys.append(y[i + self.window_size - 1])
        if y is not None:
            return np.array(Xs), np.array(ys)
        return np.array(Xs)

    def _get_model_class(self, input_size: int):
        import torch.nn as nn

        class SimpleLSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size,
                    hidden_size,
                    num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0.0,
                )
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(hidden_size, 1)
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                # x shape: (batch, seq_len, features)
                out, _ = self.lstm(x)
                # Take last time step
                out = out[:, -1, :]
                out = self.dropout(out)
                out = self.fc(out)
                return self.sigmoid(out)

        return SimpleLSTM

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LSTMDirectionalClassifier:
        """Fit the scaler and train the PyTorch LSTM."""
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, TensorDataset

        torch.set_num_threads(1)  # Thread-limited for safety in pipelines

        missing = [f for f in self.features if f not in X.columns]
        if missing:
            self.features = [f for f in self.features if f in X.columns]

        X_clean = X[self.features].fillna(0)  # Simple fill for sequences
        y_clean = y.loc[X_clean.index]

        # Scale data
        X_scaled = self.scaler.fit_transform(X_clean.values)

        # Create rolling windows
        X_seq, y_seq = self._create_dataset(X_scaled, y_clean.values)

        if len(X_seq) < 10:
            logger.warning("Not enough data to train LSTM, skipping.")
            return self

        # Train/val split for early stopping
        X_t, X_v, y_t, y_v = train_test_split(X_seq, y_seq, test_size=0.2, shuffle=False)

        # Pos weight equivalent (BCEWithLogitsLoss takes pos_weight, but we use BCELoss)
        # We will just use BCELoss and let dropout handle some regularization

        train_data = TensorDataset(
            torch.tensor(X_t, dtype=torch.float32),
            torch.tensor(y_t, dtype=torch.float32).unsqueeze(1),
        )
        val_data = TensorDataset(
            torch.tensor(X_v, dtype=torch.float32),
            torch.tensor(y_v, dtype=torch.float32).unsqueeze(1),
        )

        train_loader = DataLoader(train_data, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_data, batch_size=self.batch_size, shuffle=False)

        ModelClass = self._get_model_class(len(self.features))
        model = ModelClass(len(self.features), self.hidden_size, self.num_layers, self.dropout)

        criterion = nn.BCELoss()
        optimizer = optim.Adam(model.parameters(), lr=self.lr, weight_decay=1e-5)

        best_val_loss = float("inf")
        best_state = None
        patience = 5
        patience_counter = 0

        for _epoch in range(self.epochs):
            model.train()
            train_loss = 0.0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = model.state_dict()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break

        if best_state is not None:
            self.model_state_dict = best_state

        return self

    def predict_proba_batch(self, X: pd.DataFrame) -> pd.Series:
        """Predict probabilities sequentially."""
        import torch

        missing_features = [f for f in self.features if f not in X.columns]
        if missing_features:
            raise FeatureMismatchError(missing_features)

        if self.model_state_dict is None:
            return pd.Series(0.5, index=X.index)

        X_clean = X[self.features].fillna(0)
        X_scaled = self.scaler.transform(X_clean.values)

        # To predict, we need historical context.
        # In a batch setting where we just want the predictions corresponding to X.index,
        # we actually need the prior (window_size-1) elements from the DB.
        # But for pipeline simplicity (similar to XGBoost), if we only have X,
        # we will pad the beginning with zeros or repeat the first element.
        # This is a limitation of batch scoring without full history.

        # Pad X_scaled to ensure we can generate a prediction for every row in X
        pad_size = self.window_size - 1
        if pad_size > 0:
            padding = np.repeat(X_scaled[0:1], pad_size, axis=0)
            X_scaled_padded = np.vstack([padding, X_scaled])
        else:
            X_scaled_padded = X_scaled

        X_seq = self._create_dataset(X_scaled_padded)

        ModelClass = self._get_model_class(len(self.features))
        model = ModelClass(len(self.features), self.hidden_size, self.num_layers, self.dropout)
        model.load_state_dict(self.model_state_dict)
        model.eval()

        with torch.no_grad():
            tensor_x = torch.tensor(X_seq, dtype=torch.float32)
            probs = model(tensor_x).squeeze(-1).numpy()

        return pd.Series(probs, index=X.index)

    def get_feature_importances(self) -> list[dict[str, Any]]:
        # LSTM feature importance is non-trivial (requires IG or SHAP). We return empty.
        return []

    def save(self, path: Path | str) -> None:
        """Save model state to a file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "scaler": self.scaler,
            "features": self.features,
            "model_state_dict": self.model_state_dict,
            "window_size": self.window_size,
            "hidden_size": self.hidden_size,
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path | str) -> LSTMDirectionalClassifier | None:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                state = pickle.load(f)

            inst = cls(
                window_size=state.get("window_size", 5), hidden_size=state.get("hidden_size", 16)
            )
            inst.scaler = state.get("scaler")
            inst.features = state.get("features", inst.features)
            inst.model_state_dict = state.get("model_state_dict")
            return inst
        except Exception as e:
            logger.error(f"Failed to load LSTM model from {path}: {e}")
            return None
