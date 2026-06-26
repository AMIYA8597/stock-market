from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from research.feature_engineering.pipeline import FeaturePipeline
from research.feature_engineering.price_factors import PriceFactorsBuilder


def _build_input_frame(rows: int = 320) -> pd.DataFrame:
    time_index = pd.date_range(end=datetime.now(UTC), periods=rows, freq="D")
    close = 100 + np.cumsum(np.linspace(-0.5, 0.8, rows))
    open_ = close * (1 - 0.002)
    high = close * 1.01
    low = close * 0.99
    volume = np.linspace(100_000, 200_000, rows)

    return pd.DataFrame(
        {
            "time": time_index,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "symbol": "RELIANCE.NS",
            "symbol_id": 1,
            "interval": "1d",
            "exchange": "NSE",
            "sector": "Energy",
            "industry": "Integrated",
            "name": "Reliance Industries",
            "adjusted_close": close,
        }
    )


def test_feature_pipeline_creates_expected_core_features() -> None:
    frame = _build_input_frame()
    pipeline = FeaturePipeline()

    out = pipeline.run(frame)

    required_columns = {
        "ret_1d",
        "ret_5d",
        "momentum_21d",
        "parkinson_vol_21d",
        "yang_zhang_vol_21d",
        "drawdown",
    }

    missing = required_columns.difference(set(out.columns))
    assert not missing

    numeric = out.select_dtypes(include=[np.number])
    values = numeric.to_numpy(dtype=float, copy=True)
    assert np.isfinite(values[~np.isnan(values)]).all()


def test_feature_pipeline_ret_1d_is_causality_safe() -> None:
    frame = _build_input_frame(rows=80)
    pipeline = FeaturePipeline(builders=[PriceFactorsBuilder()])
    out = pipeline.run(frame)

    expected = np.log(frame["close"].astype(float) / frame["close"].astype(float).shift(1))
    pd.testing.assert_series_equal(out["ret_1d"], expected, check_names=False)


def test_chart_patterns_builder() -> None:
    from research.feature_engineering.chart_patterns import ChartPatternsBuilder
    frame = _build_input_frame(rows=100)
    builder = ChartPatternsBuilder()
    out = builder.transform(frame)

    required_pattern_cols = {
        "pattern_double_top",
        "pattern_double_bottom",
        "pattern_head_shoulders",
        "pattern_inv_head_shoulders",
        "pattern_ascending_triangle",
        "pattern_descending_triangle",
        "pattern_symmetrical_triangle"
    }
    missing = required_pattern_cols.difference(set(out.columns))
    assert not missing
    assert (out[list(required_pattern_cols)].isin([0.0, 1.0])).all().all()
