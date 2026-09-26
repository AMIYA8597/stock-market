import pandas as pd

from app.data_platform.validation import validate_ohlcv_row


def test_validate_valid_row():
    row = pd.Series({'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 102.0, 'volume': 1000})
    status, flags = validate_ohlcv_row(row)
    assert status == "VALID"
    assert len(flags) == 0

def test_validate_invalid_prices():
    row = pd.Series({'open': -10.0, 'high': 105.0, 'low': 95.0, 'close': 102.0, 'volume': 1000})
    status, flags = validate_ohlcv_row(row)
    assert status == "INVALID"
    assert "invalid_open" in flags

def test_validate_ohlc_consistency():
    # High is less than open
    row = pd.Series({'open': 100.0, 'high': 90.0, 'low': 80.0, 'close': 95.0, 'volume': 1000})
    status, flags = validate_ohlcv_row(row)
    assert status == "INVALID"
    assert "high_less_than_open_or_close" in flags

def test_validate_zero_volume_warning():
    row = pd.Series({'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 102.0, 'volume': 0})
    status, flags = validate_ohlcv_row(row)
    assert status == "WARNING"
    assert "zero_volume" in flags
