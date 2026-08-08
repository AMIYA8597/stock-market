import os
import sys
import pandas as pd
import numpy as np

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.regime_analyzer import HMMRegimeModel
import yfinance as yf

def trace_regime():
    print("Fetching RELIANCE.NS data...")
    ticker = yf.Ticker("RELIANCE.NS")
    df = ticker.history(period="3y")
    
    # Preprocess exactly as in regime_tasks.py
    df["returns"] = np.log(df["Close"] / df["Close"].shift(1))
    df["volatility_20d"] = df["returns"].rolling(20).std() * np.sqrt(252)
    
    features = df[["returns", "volatility_20d"]].dropna()
    
    print("Fitting HMM...")
    hmm = HMMRegimeModel(n_states=3)
    hmm.fit(features)
    
    print("Predicting states...")
    # Predict all historical points to trace the path
    hidden_states = hmm.model.predict(features.values)
    mapping = hmm.map_states_to_labels(features)
    
    features["regime_label"] = [mapping.get(s, "unknown") for s in hidden_states]
    
    print("\n--- Regime Transitions ---")
    current_regime = None
    for idx, row in features.iterrows():
        label = row["regime_label"]
        if label != current_regime:
            print(f"{idx.date()}: Transitioned to {label.upper()}")
            current_regime = label

if __name__ == "__main__":
    trace_regime()
