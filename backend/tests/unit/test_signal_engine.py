import numpy as np
import pandas as pd

from app.services.signal_engine import TechnicalSignalEngine


def test_generate_signal_neutral_small_data():
    """Test that small data returns neutral signal."""
    df = pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "close": [102.0] * 10,
            "volume": [1000] * 10,
        }
    )

    result = TechnicalSignalEngine.generate_signal(df)
    assert result["direction"] == "NEUTRAL"
    assert result["confidence"] == 0.0
    assert result["score"] == 0.0


def test_generate_signal_valid_data():
    """Test generating a signal with valid OHLCV data."""
    # Create 100 rows of dummy data with enough volatility
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "open": np.random.rand(100) * 10 + 100,
            "high": np.random.rand(100) * 10 + 105,
            "low": np.random.rand(100) * 10 + 90,
            "close": np.random.rand(100) * 10 + 100,
            "volume": np.random.randint(1000, 5000, 100),
        }
    )

    result = TechnicalSignalEngine.generate_signal(df)

    assert "direction" in result
    assert result["direction"] in ["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert -1.0 <= result["score"] <= 1.0
    assert "breakdown" in result
    assert isinstance(result["breakdown"], dict)

    # Assert breakdown has items (some rules must have triggered)
    assert len(result["breakdown"]) > 0

    # Assert stop_loss and take_profit exist
    assert result["stop_loss"] >= 0.0
    assert result["take_profit"] >= 0.0
    assert result["position_size_pct"] >= 0.0
