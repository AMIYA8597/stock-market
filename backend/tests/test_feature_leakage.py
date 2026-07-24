import numpy as np
import pandas as pd

from research.feature_engineering.pipeline import FeaturePipeline


def test_feature_pipeline_no_lookahead_leakage():
    """
    Tests that the feature pipeline is strictly causality-safe.
    Features at time t should be identical whether computed on data up to t,
    or on data up to t+N. Future data must not leak into past feature values.
    """
    # 1. Generate synthetic OHLCV data for 300 days
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=300, freq="B")

    # Random walk price
    returns = np.random.normal(loc=0.0001, scale=0.02, size=300)
    price = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        "time": dates,
        "symbol": "TEST",
        "open": price * np.random.uniform(0.99, 1.01, size=300),
        "high": price * np.random.uniform(1.0, 1.03, size=300),
        "low": price * np.random.uniform(0.97, 1.0, size=300),
        "close": price,
        "volume": np.random.randint(1000, 1000000, size=300).astype(float),
    })

    # Add mock Fama-French factors for FF5BetasBuilder
    df["mkt_rf"] = np.random.normal(0, 0.01, size=300)
    df["smb"] = np.random.normal(0, 0.01, size=300)
    df["hml"] = np.random.normal(0, 0.01, size=300)
    df["rmw"] = np.random.normal(0, 0.01, size=300)
    df["cma"] = np.random.normal(0, 0.01, size=300)

    # 2. Split into data up to T, and data up to T+10
    T = 250
    df_past = df.iloc[:T].copy()
    df_future = df.iloc[:T+10].copy()

    # 3. Run feature pipeline
    pipeline = FeaturePipeline()

    features_past = pipeline.run(df_past)
    features_future = pipeline.run(df_future)

    # 4. Extract features exactly at time T-1 (the last row of df_past)
    t_minus_1 = df_past["time"].iloc[-1]

    row_past = features_past[features_past["time"] == t_minus_1].iloc[0]
    row_future = features_future[features_future["time"] == t_minus_1].iloc[0]

    # 5. Assert equality for all numeric columns (ignoring NaNs)
    numeric_cols = features_past.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        val_past = row_past[col]
        val_future = row_future[col]

        if pd.isna(val_past) and pd.isna(val_future):
            continue

        assert np.isclose(val_past, val_future, equal_nan=True), (
            f"Leakage detected in feature '{col}'. "
            f"Value at T without future: {val_past}, "
            f"Value at T with future: {val_future}"
        )
