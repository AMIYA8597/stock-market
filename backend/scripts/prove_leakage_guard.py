from __future__ import annotations

import numpy as np
import pandas as pd


class LeakageError(Exception):
    pass


def calculate_metrics(predictions: np.ndarray, actual_returns: np.ndarray, close_prices: np.ndarray) -> dict:
    hits = (predictions * np.sign(actual_returns)) > 0
    hit_rate = np.mean(hits) if len(hits) > 0 else 0.5
    return {"hit_rate": hit_rate}


def run_backtest_with_guard(df: pd.DataFrame):
    """Simulate the backtest pipeline with the Honesty Guard."""

    # 1. Simulate a model that uses the 'leaky_feature' to make predictions
    # A model trained on a leaky feature will perfectly learn to output 1 when leaky_feature > 0
    predictions = np.where(df['leaky_feature'] > 0, 1.0, -1.0)

    actual_returns = df['target_5d'].values
    closes = df['close'].values

    metrics = calculate_metrics(predictions, actual_returns, closes)
    hit_rate = metrics["hit_rate"]

    print(f"Calculated hit rate for model: {hit_rate*100:.2f}%")

    # ANTI-LEAKAGE GUARD (HONESTY LAW)
    if hit_rate > 0.75:
        raise LeakageError(f"Look-ahead bias detected! Directional accuracy of {hit_rate*100:.1f}% exceeds realistic market efficiency (75% max). Pipeline aborted.")

    print("Backtest passed successfully.")


def main():
    print("Generating synthetic price data...")
    # Generate 100 days of random price data
    np.random.seed(42)
    closes = np.cumsum(np.random.randn(100)) + 100
    df = pd.DataFrame({"close": closes})

    # Target: 5-day forward return
    df['target_5d'] = (df['close'].shift(-5) / df['close']) - 1.0

    print("Injecting synthetic leaky feature into the dataset (looking 5 days into the future)...")
    # THE LEAK: Feature uses close price 5 days into the future!
    df['leaky_feature'] = (df['close'].shift(-5) / df['close']) - 1.0

    df = df.dropna()

    try:
        run_backtest_with_guard(df)
    except LeakageError as e:
        print("\n[SUCCESS] Guard successfully caught the leakage!")
        print(f"Guard output: {e}")

if __name__ == "__main__":
    main()

