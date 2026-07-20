import os
import pickle
import torch
import numpy as np
from .data_service import get_historical
from .indicator_service import compute_indicators

# Directory where serialized models are stored
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def load_model(model_name: str):
    """Load a trained model by name.
    Supports 'arima', 'prophet', 'lstm', 'cnn', 'xgboost'.
    Returns a callable that takes a DataFrame of recent data and returns a prediction.
    """
    path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
    if model_name.lower() in ('arima', 'prophet', 'xgboost'):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file {path} not found")
        with open(path, 'rb') as fh:
            model = pickle.load(fh)
        return model
    elif model_name.lower() == 'lstm':
        # Assume a torch model saved via torch.save
        pt_path = os.path.join(MODEL_DIR, 'lstm.pt')
        if not os.path.exists(pt_path):
            raise FileNotFoundError(f"LSTM model {pt_path} not found")
        model = torch.load(pt_path, map_location='cpu')
        model.eval()
        return model
    elif model_name.lower() == 'cnn':
        pt_path = os.path.join(MODEL_DIR, 'cnn.pt')
        if not os.path.exists(pt_path):
            raise FileNotFoundError(f"CNN model {pt_path} not found")
        model = torch.load(pt_path, map_location='cpu')
        model.eval()
        return model
    else:
        raise ValueError(f"Unsupported model: {model_name}")

def predict_price(ticker: str, model_name: str = 'lstm'):
    """Simple wrapper that returns a next‑step price prediction.
    For demo purposes, if the requested model file is missing we fall back to a
    naive forecast using the last close price plus a small random walk.
    """
    try:
        model = load_model(model_name)
    except Exception as e:
        # Fallback to naive prediction
        recent = get_historical(ticker, days=5)
        if not recent:
            raise RuntimeError('No data to forecast')
        last_close = recent[-1]['close']
        # add small random perturbation (±0.5%)
        perturb = np.random.uniform(-0.005, 0.005) * last_close
        return round(last_close + perturb, 4)

    # Prepare input depending on model type
    if model_name.lower() in ('arima', 'prophet', 'xgboost'):
        # Assume the model implements a .forecast() method returning a scalar
        recent = get_historical(ticker, days=30)
        # Convert to pandas Series of close prices
        import pandas as pd
        series = pd.Series([d['close'] for d in recent])
        forecast = model.forecast(series)
        return float(forecast)
    elif model_name.lower() == 'lstm':
        # Use last 60 close prices as input sequence
        recent = get_historical(ticker, days=60)
        closes = np.array([d['close'] for d in recent], dtype=np.float32)
        seq = torch.from_numpy(closes).unsqueeze(0).unsqueeze(-1)  # shape (1,60,1)
        with torch.no_grad():
            pred = model(seq)
        return float(pred.squeeze().item())
    elif model_name.lower() == 'cnn':
        # Placeholder: treat same as LSTM for now
        recent = get_historical(ticker, days=60)
        closes = np.array([d['close'] for d in recent], dtype=np.float32)
        seq = torch.from_numpy(closes).unsqueeze(0).unsqueeze(-1)
        with torch.no_grad():
            pred = model(seq)
        return float(pred.squeeze().item())
    else:
        raise ValueError('Unsupported model')
