from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.instrument import Instrument
from app.services.signal_engine import SignalEngine, TechnicalSignalEngine


def create_mock_df(positive: bool = True):
    rows = 60
    df = pd.DataFrame()
    df["close"] = np.linspace(100, 200, rows) if positive else np.linspace(200, 100, rows)
    df["open"] = df["close"] - 1 if positive else df["close"] + 1
    df["high"] = df["close"] + 2
    df["low"] = df["close"] - 2
    df["volume"] = np.linspace(1000, 5000, rows)

    # Trend
    df["SMA_20"] = [100] * 58 + [150, 160] if positive else [160] * 58 + [150, 100]
    df["SMA_50"] = [150] * 60 if positive else [150] * 60
    df["MACDh_12"] = [1, 2] * 30 if positive else [-1, -2] * 30
    df["ADX_14"] = [30] * 60
    df["DMP_14"] = [40] * 60 if positive else [10] * 60
    df["DMN_14"] = [10] * 60 if positive else [40] * 60
    df["SUPERTd_7"] = [1] * 60 if positive else [-1] * 60

    if positive:
        df["PSARl_0.2"] = [150] * 60
    else:
        df["PSARs_0.2"] = [150] * 60

    # Momentum
    df["RSI_14"] = [20] * 60 if positive else [80] * 60
    df["STOCHk_14"] = [10] * 60 if positive else [90] * 60
    df["STOCHd_14"] = [10] * 60 if positive else [90] * 60
    df["ROC_10"] = [1] * 60 if positive else [-1] * 60
    df["CCI_14"] = [150] * 60 if positive else [-150] * 60
    df["WILLR_14"] = [-90] * 60 if positive else [-10] * 60

    # Volatility
    df["BBP_5"] = [0.01] * 60 if positive else [0.99] * 60
    df["BBB_5"] = [4] * 60
    df["KCU_20"] = [100] * 60 if positive else [300] * 60
    df["KCL_20"] = [100] * 60 if positive else [300] * 60
    df["DCU_20"] = [100] * 60 if positive else [300] * 60
    df["DCL_20"] = [100] * 60 if positive else [300] * 60

    # Volume
    df["OBV"] = np.linspace(1000, 2000, rows) if positive else np.linspace(2000, 1000, rows)
    df["VWAP"] = [100] * 60 if positive else [300] * 60
    df["MFI_14"] = [10] * 60 if positive else [90] * 60

    df["ATRr_14"] = [2] * 60

    return df

@patch("app.services.signal_engine.get_pattern_score")
def test_technical_signal_engine_positive(mock_get_pattern_score):
    mock_get_pattern_score.return_value = {"pattern_score": 0.5, "patterns_detected": ["Bullish"]}
    df = create_mock_df(positive=True)
    with patch("pandas.core.frame.DataFrame.ta", create=True, new_callable=MagicMock):
        res = TechnicalSignalEngine.generate_signal(df)
    assert res["direction"] in ["BUY", "STRONG_BUY"]

@patch("app.services.signal_engine.get_pattern_score")
def test_technical_signal_engine_negative(mock_get_pattern_score):
    mock_get_pattern_score.return_value = {"pattern_score": -0.5, "patterns_detected": ["Bearish"]}
    df = create_mock_df(positive=False)
    with patch("pandas.core.frame.DataFrame.ta", create=True, new_callable=MagicMock):
        res = TechnicalSignalEngine.generate_signal(df)
    assert res["direction"] in ["SELL", "STRONG_SELL"]

@patch("app.services.signal_engine.get_pattern_score")
def test_technical_signal_engine_short_df(mock_get_pattern_score):
    df = pd.DataFrame({"close": [1, 2, 3]}) # less than 50 rows
    res = TechnicalSignalEngine.generate_signal(df)
    assert res["direction"] == "NEUTRAL"
    assert res["confidence"] == 0.0
@pytest.mark.asyncio
@patch("research.backtesting.cost_model.compute_indian_costs")
async def test_process_new_prediction(mock_costs):
    mock_costs.return_value = np.array([[100.0]])
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_result = MagicMock()
    mock_instrument = Instrument(id=1, symbol="RELIANCE")
    mock_result.scalar_one_or_none.return_value = mock_instrument
    mock_db.execute.return_value = mock_result

    pred = {
        "direction": "BUY",
        "confidence": 0.8,
        "raw_ensemble": 0.85,
        "regime": {"regime": "BULL", "conditional_vol": 0.02},
        "target_price_5d": 3000.0,
        "stop_loss": 2000.0,
        "technical": {"last_close": 2100.0, "score": 0.5}
    }

    res = await SignalEngine.process_new_prediction(mock_db, "RELIANCE", pred)
    assert res is not None
    assert res.symbol_id == 1
    assert res.direction == "BUY"

@pytest.mark.asyncio
async def test_process_new_prediction_no_instrument():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    res = await SignalEngine.process_new_prediction(mock_db, "UNKNOWN", {})
    assert res is None

@pytest.mark.asyncio
async def test_process_new_prediction_low_confidence():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_instrument = Instrument(id=1, symbol="RELIANCE")
    mock_result.scalar_one_or_none.return_value = mock_instrument
    mock_db.execute.return_value = mock_result

    pred = {"direction": "BUY", "confidence": 0.5} # < 0.65
    res = await SignalEngine.process_new_prediction(mock_db, "RELIANCE", pred)
    assert res is None

@pytest.mark.asyncio
async def test_process_new_prediction_incompatible_regime_buy():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_instrument = Instrument(id=1, symbol="RELIANCE")
    mock_result.scalar_one_or_none.return_value = mock_instrument
    mock_db.execute.return_value = mock_result

    pred = {"direction": "BUY", "confidence": 0.8, "regime": {"regime": "BEAR"}}
    res = await SignalEngine.process_new_prediction(mock_db, "RELIANCE", pred)
    assert res is None

@pytest.mark.asyncio
async def test_process_new_prediction_incompatible_regime_sell():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_instrument = Instrument(id=1, symbol="RELIANCE")
    mock_result.scalar_one_or_none.return_value = mock_instrument
    mock_db.execute.return_value = mock_result

    pred = {"direction": "SELL", "confidence": 0.8, "regime": {"regime": "BULL"}}
    res = await SignalEngine.process_new_prediction(mock_db, "RELIANCE", pred)
    assert res is None

@pytest.mark.asyncio
@patch("research.backtesting.cost_model.compute_indian_costs")
async def test_process_new_prediction_low_expected_gain(mock_costs):
    mock_costs.return_value = np.array([[500.0]]) # high cost
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_instrument = Instrument(id=1, symbol="RELIANCE")
    mock_result.scalar_one_or_none.return_value = mock_instrument
    mock_db.execute.return_value = mock_result

    pred = {
        "direction": "BUY",
        "confidence": 0.8,
        "regime": {"regime": "BULL"},
        "target_price_5d": 2110.0, # low gain vs cost
        "technical": {"last_close": 2100.0}
    }

    res = await SignalEngine.process_new_prediction(mock_db, "RELIANCE", pred)
    assert res is None
