
import numpy as np
import pandas as pd

from research.feature_engineering.pipeline import FeaturePipeline


def test_anti_leakage_feature_pipeline():
    """Test that features at time t are identical when computed with or without data > t.

    This ensures there is no look-ahead bias (leakage) in the feature engineering pipeline.
    """

    # Generate synthetic OHLCV data for 200 days
    dates = pd.date_range(start="2024-01-01", periods=200, freq="D")

    np.random.seed(42)
    # Random walk price
    returns = np.random.normal(loc=0.0005, scale=0.015, size=200)
    close_prices = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "time": dates,
        "open": close_prices * (1 + np.random.normal(0, 0.005, 200)),
        "high": close_prices * (1 + np.abs(np.random.normal(0, 0.01, 200))),
        "low": close_prices * (1 - np.abs(np.random.normal(0, 0.01, 200))),
        "close": close_prices,
        "volume": np.random.randint(1000, 100000, 200),
    })

    pipeline = FeaturePipeline()

    # 1. Compute features using the full dataset (data up to t + future)
    full_features = pipeline.run(df)

    # 2. Compute features using truncated dataset (data up to t)
    # Let's say t is index 150
    t_idx = 150
    truncated_df = df.iloc[:t_idx + 1].copy()

    truncated_features = pipeline.run(truncated_df)

    # Extract the row for time t in both datasets
    row_t_full = full_features.iloc[t_idx]
    row_t_truncated = truncated_features.iloc[t_idx]

    # Assert that all features at time t are IDENTICAL
    # Ignore time/ohlcv columns
    skip_cols = ["time", "open", "high", "low", "close", "volume"]
    feature_cols = [c for c in full_features.columns if c not in skip_cols]

    mismatches = []

    for col in feature_cols:
        val_full = row_t_full[col]
        val_trunc = row_t_truncated[col]

        # Handle NaNs
        if pd.isna(val_full) and pd.isna(val_trunc):
            continue

        # Float comparisons
        if isinstance(val_full, (float, np.floating)):
            if not np.isclose(val_full, val_trunc, equal_nan=True):
                mismatches.append((col, val_full, val_trunc))
        else:
            if val_full != val_trunc:
                mismatches.append((col, val_full, val_trunc))

    if mismatches:
        print("\n--- ANTI-LEAKAGE TEST FAILED ---")
        for m in mismatches:
            print(f"Feature: {m[0]} | Full: {m[1]} | Truncated: {m[2]}")

    assert len(mismatches) == 0, f"Found {len(mismatches)} leaking features!"
    print(f"\nAnti-leakage test passed! Checked {len(feature_cols)} features.")
