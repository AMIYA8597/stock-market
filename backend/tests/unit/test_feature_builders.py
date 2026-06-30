import numpy as np
import pandas as pd
from app.research.feature_engineering.price_factors import PriceFactorsBuilder
from app.research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

def _build_synthetic_df(rows: int = 150) -> pd.DataFrame:
    dates = pd.date_range(end="2026-06-27", periods=rows, freq="D")
    
    # Generate prices that fluctuate with some realistic path
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, rows)
    close = 100.0 * np.exp(np.cumsum(returns))
    open_ = close * (1.0 - 0.002 * np.random.rand(rows))
    high = np.maximum(open_, close) * (1.0 + 0.005 * np.random.rand(rows))
    low = np.minimum(open_, close) * (1.0 - 0.005 * np.random.rand(rows))
    volume = np.random.randint(100_000, 1_000_000, rows).astype(float)
    
    return pd.DataFrame({
        "time": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)

def test_price_factors_builder_output_quality():
    df = _build_synthetic_df()
    builder = PriceFactorsBuilder()
    out_df = builder.build(df)
    
    # Assert no output column is entirely NaN
    for col in out_df.columns:
        # Allow first few rows to be NaN due to shift/rolling windows, but not the entire column
        non_nan_count = out_df[col].notna().sum()
        assert non_nan_count > 0, f"Column {col} is entirely NaN"
        
        # Check that it's not a single repeated value (except for sparse binary/trinary candlestick flags)
        if not col.startswith("CDL_"):
            unique_vals = out_df[col].dropna().unique()
            assert len(unique_vals) > 1, f"Column {col} contains only one unique value: {unique_vals[0]}"

def test_volatility_factors_builder_output_quality():
    df = _build_synthetic_df()
    builder = VolatilityFactorsBuilder()
    out_df = builder.build(df)
    
    # Assert no output column is entirely NaN
    for col in out_df.columns:
        non_nan_count = out_df[col].notna().sum()
        assert non_nan_count > 0, f"Column {col} is entirely NaN"
        
        # Check that it's not a single repeated value
        unique_vals = out_df[col].dropna().unique()
        assert len(unique_vals) > 1, f"Column {col} contains only one unique value: {unique_vals[0]}"
