import numpy as np
import torch
import torch.nn as nn
from typing import Tuple

class SimpleLSTMForecaster(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x shape: (batch, seq_len, 1)
        lstm_out, _ = self.lstm(x)
        # We only want the last time step prediction
        predictions = self.linear(lstm_out[:, -1, :])
        return predictions

def deep_learning_forecast(closes: np.ndarray, steps: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Trains a lightweight LSTM on the fly (or runs inference) to predict future prices.
    Since we need extreme speed for API requests, we train it very briefly on the recent window.
    """
    if len(closes) < 20:
        # Fallback if extremely little data
        return _fallback_forecast(closes, steps)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Normalize data
    mean_val = np.mean(closes)
    std_val = np.std(closes) + 1e-8
    norm_closes = (closes - mean_val) / std_val

    # Create sequences
    seq_length = min(20, len(closes) - 5)
    X, y = [], []
    for i in range(len(norm_closes) - seq_length):
        X.append(norm_closes[i:i+seq_length])
        y.append(norm_closes[i+seq_length])

    X = torch.tensor(np.array(X), dtype=torch.float32).unsqueeze(-1).to(device)
    y = torch.tensor(np.array(y), dtype=torch.float32).unsqueeze(-1).to(device)

    model = SimpleLSTMForecaster(1, 32, 1).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    # Train very fast (10 epochs) just to capture local dynamics
    model.train()
    for _ in range(15):
        optimizer.zero_grad()
        out = model(X)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()

    # Autoregressive multi-step prediction
    model.eval()
    current_seq = norm_closes[-seq_length:].tolist()

    predictions_norm = []
    with torch.no_grad():
        for _ in range(steps):
            seq_tensor = torch.tensor([current_seq[-seq_length:]], dtype=torch.float32).unsqueeze(-1).to(device)
            pred = model(seq_tensor).item()
            predictions_norm.append(pred)
            current_seq.append(pred)

    # Denormalize
    predictions = (np.array(predictions_norm) * std_val) + mean_val

    # Calculate confidence intervals based on historical variance
    ci_width = std_val * np.sqrt(np.arange(1, steps + 1)) * 0.3
    pred_ci = np.column_stack([predictions - ci_width, predictions + ci_width])

    return predictions, pred_ci

def _fallback_forecast(closes: np.ndarray, steps: int) -> Tuple[np.ndarray, np.ndarray]:
    current = float(closes[-1])
    pred_mean = np.full(steps, current)
    pred_ci = np.column_stack([pred_mean * 0.97, pred_mean * 1.03])
    return pred_mean, pred_ci
