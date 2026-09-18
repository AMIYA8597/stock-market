
import numpy as np
import torch
import torch.nn as nn


class SimpleLSTMForecaster(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, model_type="lstm"):
        super().__init__()
        self.model_type = model_type.lower()
        if self.model_type == "lstm":
            self.rnn = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.linear = nn.Linear(hidden_size, 1)
        elif self.model_type == "bilstm":
            self.rnn = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, bidirectional=True)
            self.linear = nn.Linear(hidden_size * 2, 1)
        elif self.model_type == "gru":
            self.rnn = nn.GRU(input_size, hidden_size, num_layers, batch_first=True)
            self.linear = nn.Linear(hidden_size, 1)
        elif self.model_type == "cnn_lstm":
            self.cnn = nn.Conv1d(in_channels=input_size, out_channels=16, kernel_size=3, padding=1)
            self.rnn = nn.LSTM(16, hidden_size, num_layers, batch_first=True)
            self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        if self.model_type == "cnn_lstm":
            # x shape: (batch, seq_len, input_size)
            x_cnn = x.transpose(1, 2)
            x_cnn = torch.relu(self.cnn(x_cnn))
            x = x_cnn.transpose(1, 2)

        out, _ = self.rnn(x)
        predictions = self.linear(out[:, -1, :])
        return predictions

def deep_learning_forecast(closes: np.ndarray, steps: int, model_type="lstm") -> tuple[np.ndarray, np.ndarray]:
    if len(closes) < 20:
        return _fallback_forecast(closes, steps)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    mean_val = np.mean(closes)
    std_val = np.std(closes) + 1e-8
    norm_closes = (closes - mean_val) / std_val

    seq_length = min(20, len(closes) - 5)
    X, y = [], []
    for i in range(len(norm_closes) - seq_length):
        X.append(norm_closes[i:i+seq_length])
        y.append(norm_closes[i+seq_length])

    X = torch.tensor(np.array(X), dtype=torch.float32).unsqueeze(-1).to(device)
    y = torch.tensor(np.array(y), dtype=torch.float32).unsqueeze(-1).to(device)

    model = SimpleLSTMForecaster(1, 32, 1, model_type=model_type).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    model.train()
    for _ in range(15):
        optimizer.zero_grad()
        out = model(X)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()

    model.eval()
    current_seq = norm_closes[-seq_length:].tolist()

    predictions_norm = []
    with torch.no_grad():
        for _ in range(steps):
            seq_tensor = torch.tensor([current_seq[-seq_length:]], dtype=torch.float32).unsqueeze(-1).to(device)
            pred = model(seq_tensor).item()
            predictions_norm.append(pred)
            current_seq.append(pred)

    predictions = (np.array(predictions_norm) * std_val) + mean_val
    ci_width = std_val * np.sqrt(np.arange(1, steps + 1)) * 0.3
    pred_ci = np.column_stack([predictions - ci_width, predictions + ci_width])

    return predictions, pred_ci

def _fallback_forecast(closes: np.ndarray, steps: int) -> tuple[np.ndarray, np.ndarray]:
    current = float(closes[-1])
    pred_mean = np.full(steps, current)
    pred_ci = np.column_stack([pred_mean * 0.97, pred_mean * 1.03])
    return pred_mean, pred_ci
