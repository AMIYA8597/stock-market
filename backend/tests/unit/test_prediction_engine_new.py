import importlib
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import numpy as np
import pandas as pd
import pytest

from app.services import prediction_engine as prediction_engine_module

# conftest.py maliciously overrides get_full_prediction globally.
# We must reload the module to restore the original function for our tests.
importlib.reload(prediction_engine_module)

from app.services.prediction_engine import (
    _cache_fetch,
    _cache_store,
    _fit_and_forecast,
    _in_memory_prediction_cache,
    build_ensemble_signal,
    build_ensemble_signal_sync,
    compute_kelly_fraction,
    detect_regime,
    forecast_multi_horizon,
    forecast_prices,
    get_full_prediction,
    standardize_df_columns,
)


@pytest.fixture(autouse=True)
def clear_caches():
    _in_memory_prediction_cache.clear()
    from app.services.prediction_engine import _HMM_CACHE, _MODEL_CACHE
    _HMM_CACHE.clear()
    _MODEL_CACHE.clear()
    yield
    _in_memory_prediction_cache.clear()
    _HMM_CACHE.clear()
    _MODEL_CACHE.clear()

@pytest.fixture
def sample_df():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
    df = pd.DataFrame({
        'open': np.random.randn(100) + 100,
        'high': np.random.randn(100) + 105,
        'low': np.random.randn(100) + 95,
        'close': np.random.randn(100) + 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    df.attrs['symbol'] = 'TEST'
    return df

@pytest.mark.asyncio
async def test_cache_fetch_and_store():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps({"test": "data"})
    with patch("app.database.redis_client.get_redis", return_value=mock_redis):
        res = await _cache_fetch("test_sym")
        assert res == {"test": "data"}
        res2 = await _cache_fetch("test_sym")
        assert res2 == {"test": "data"}
        await _cache_store("test_sym2", {"val": 1})
        res3 = await _cache_fetch("test_sym2")
        assert res3 == {"val": 1}

@pytest.mark.asyncio
async def test_cache_redis_error():
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis error")
    with patch("app.database.redis_client.get_redis", return_value=mock_redis):
        res = await _cache_fetch("error_sym")
        assert res is None

def test_get_sentiment_pipeline():
    with patch.dict('sys.modules', {'transformers': MagicMock()}):
        from app.services import prediction_engine
        prediction_engine._SENTIMENT_PIPELINE = None
        pipe = prediction_engine.get_sentiment_pipeline()
        assert pipe is not None

def test_detect_regime_short_df():
    df = pd.DataFrame({"close": [1, 2, 3]})
    import pytest
    with pytest.raises(ValueError, match="Insufficient data"):
        detect_regime(df)

def test_detect_regime_success(sample_df):
    mock_engine_class = MagicMock()
    mock_engine = mock_engine_class.return_value
    mock_res = MagicMock()
    mock_res.current_state = 0
    mock_res.state_probs = [0.8, 0.1, 0.05, 0.05]
    mock_res.conditional_vol = 0.02
    mock_res.vol_forecast_5d = [0.03]
    mock_res.vol_forecast_21d = [0.05]
    mock_engine.predict.return_value = mock_res
    mock_engine.get_transition_matrix.return_value = np.array([[1, 0], [0, 1]])

    with patch.dict('sys.modules', {'research.models.hmm_garch.inference': MagicMock(InferenceEngine=mock_engine_class)}):
        res = detect_regime(sample_df)
        assert res["regime"] == "BULL"
        assert res["hmm_used"] is True

def test_detect_regime_fallback(sample_df):
    with patch.dict('sys.modules', {'research.models.hmm_garch.inference': MagicMock()}):
        import sys
        sys.modules['research.models.hmm_garch.inference'].InferenceEngine.side_effect = Exception("fail")
        res = detect_regime(sample_df)
        assert res["hmm_used"] is False

def test_compute_kelly_fraction():
    res = compute_kelly_fraction("TEST", 0.5, 0.8)
    assert isinstance(res, float)

    with patch("app.services.prediction_engine.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data='{"win_rate": 0.6, "payoff_ratio": 1.5}')):
        res2 = compute_kelly_fraction("TEST2", 0.5, 0.8)
        assert isinstance(res2, float)

def test_standardize_df_columns():
    df = pd.DataFrame({"rsi_14_col": [1, 2], "macdh_12": [3, 4], "bbp_20_2": [1,2], "atr_14": [1,2], "adx_14": [1,2]})
    exp = ["RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14", "ADX_14", "missing"]
    res = standardize_df_columns(df, exp)
    assert "missing" in res.columns
    assert "RSI_14" in res.columns

def test_build_ensemble_signal_sync(sample_df):
    sample_df["ATRr_14"] = 0.5
    with patch("app.services.prediction_engine.detect_regime") as mock_regime, \
         patch("app.services.prediction_engine.compute_kelly_fraction", return_value=0.1):

        mock_regime.return_value = {
            "regime": "BULL", "bull_prob": 0.8, "bear_prob": 0.1,
            "regime_confidence": 0.8, "hmm_used": True,
            "conditional_vol": 0.02, "vol_forecast_5d": 0.045, "vol_forecast_21d": 0.09
        }
        

        with patch.dict('sys.modules', {'research.models.xgboost_model.classifier': MagicMock()}):
            res = build_ensemble_signal_sync("TEST", sample_df)
            assert res["model_status"] in ["heuristic", "trained"]
            assert res["direction"] in ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL", "NEUTRAL"]

def test_build_ensemble_signal_all_models(sample_df):
    sample_df["ATRr_14"] = 0.5
    sample_df["close"] = 100.0
    with patch("app.services.prediction_engine.detect_regime") as mock_regime, \
         patch("app.services.prediction_engine.compute_kelly_fraction", return_value=0.1), \
         patch("app.services.sentiment_analyzer.FinBERTSentimentAnalyzer") as mock_sentiment, \
         patch("pathlib.Path.exists", return_value=True):

        mock_regime.return_value = {
            "regime": "BEAR", "bull_prob": 0.1, "bear_prob": 0.8,
            "regime_confidence": 0.8, "hmm_used": True,
            "conditional_vol": 0.02, "vol_forecast_5d": 0.045, "vol_forecast_21d": 0.09
        }
        

        mock_sentiment_inst = mock_sentiment.return_value
        mock_sentiment_inst.scrape_google_news.return_value = ["news"]
        mock_sentiment_inst.get_stock_sentiment.return_value = 0.5
        mock_sentiment_inst._initialized = True

        xgb_mock = MagicMock()
        xgb_mock.predict_proba.return_value = 0.8
        xgb_mock.get_shap_values.return_value = ([{"name": "f1", "shap_value": 0.1}], 0.5)

        lstm_mock = MagicMock()
        lstm_mock.predict_proba.return_value = (0.7, {"date1": 0.5})

        tft_mock = MagicMock()
        tft_mock.models = [1, 2, 3]
        tft_mock.quantiles = [0.1, 0.5, 0.9]
        tft_mock.features = ["close"]
        tft_mock.predict.return_value = (-0.01, 0.05, 0.1)

        gnn_mock = MagicMock()
        gnn_mock.compute_risk_factors.return_value = {"raw_signal": 0.6, "contagion_score": 0.2, "corr_to_index": 0.5}

        learner_mock = MagicMock()
        learner_mock.features = ["close"]
        learner_mock.predict_proba.return_value = 0.6

        import sys
        sys.modules['research.models.xgboost_model.classifier'] = MagicMock(XGBoostDirectionalClassifier=MagicMock(load=MagicMock(return_value=xgb_mock)))
        sys.modules['research.models.lstm_attention.classifier'] = MagicMock(LSTMAttentionClassifier=MagicMock(load=MagicMock(return_value=lstm_mock)))
        sys.modules['research.models.tft.quantile_forecaster'] = MagicMock(QuantileLGBForecaster=MagicMock(load=MagicMock(return_value=tft_mock)))
        sys.modules['research.models.gnn.contagion_risk'] = MagicMock(ContagionRiskAnalyzer=MagicMock(return_value=gnn_mock))
        sys.modules['research.models.online_learner'] = MagicMock(OnlineAdaptiveLearner=MagicMock(load=MagicMock(return_value=learner_mock)))

        res = build_ensemble_signal_sync("TEST", sample_df)
        assert res["model_status"] == "trained"

@pytest.mark.asyncio
async def test_build_ensemble_signal(sample_df):
    sample_df["ATRr_14"] = 0.5
    with patch("app.services.prediction_engine.build_ensemble_signal_sync") as mock_sync:
        mock_sync.return_value = {"test": "data"}
        res = await build_ensemble_signal("TEST", sample_df)
        assert res == {"test": "data"}

def test_fit_and_forecast():
    closes = np.linspace(100, 110, 100)
    with patch("app.services.prediction_engine._fit_and_forecast") as mock_sarimax:

        mock_sarimax.return_value = (np.log([111, 112]), np.log([[110, 112], [111, 113]]))

        mean, ci = _fit_and_forecast(closes, 2)
        assert len(mean) == 2

def test_forecast_prices(sample_df):
    with patch("app.services.prediction_engine._fit_and_forecast") as mock_sarimax:

        mock_sarimax.return_value = (np.log([101, 102, 103, 104, 105]), np.log([[100, 102]] * 5))

        res = forecast_prices(sample_df, [1, 5])
        assert len(res) == 2

@pytest.mark.asyncio
async def test_forecast_multi_horizon():
    mock_market = MagicMock()
    mock_market.get_history = AsyncMock(return_value=[{"close": 100 + i} for i in range(100)])

    with patch("app.services.market_data_service.MarketDataService.get_history", mock_market.get_history), \
         patch("app.services.prediction_engine._fit_and_forecast", return_value=(np.array([110, 111]), np.array([[105, 115], [106, 116]]))):
        res = await forecast_multi_horizon("TEST", ["1d", "invalid"])
        assert res["horizons"]["invalid"]["status"] == "error"
        assert res["horizons"]["1d"]["status"] == "ok"

@pytest.mark.asyncio
async def test_get_full_prediction(sample_df):
    mock_bar = MagicMock()
    mock_bar.time = datetime.now(UTC)
    mock_bar.open = 100
    mock_bar.high = 105
    mock_bar.low = 95
    mock_bar.close = 100
    mock_bar.volume = 1000

    with patch("app.services.market_data_service.MarketDataService._normalize_symbol", return_value="TEST"), \
         patch("app.services.prediction_engine._cache_fetch") as mock_fetch, \
         patch("app.database.connection.async_session_factory", new_callable=MagicMock) as mock_db_factory, \
         patch("research.feature_engineering.pipeline.FeaturePipeline.run", return_value=sample_df), \
         patch("pandas_ta.core.rsi"), patch("pandas_ta.core.macd"), \
         patch("pandas_ta.core.ema"), patch("pandas_ta.core.bbands"), \
         patch("pandas_ta.core.atr"), patch("pandas_ta.core.vwap"), \
         patch("pandas_ta.core.adx"), patch("pandas_ta.core.stoch"), \
         patch("pandas_ta.core.obv"), patch("pandas_ta.core.supertrend"), \
         patch("pandas_ta.core.cdl_pattern"), \
         patch("app.services.prediction_engine.build_ensemble_signal", new_callable=AsyncMock) as mock_build, \
         patch("app.services.prediction_engine.forecast_prices", return_value=[]), \
         patch("app.services.prediction_engine._cache_store", new_callable=AsyncMock), \
         patch("app.services.sr_service.SupportResistanceEngine.detect_classical_zones", return_value=[{"avg": 99, "type": "support"}]), \
         patch.dict('sys.modules', {'research.models.online_learner': MagicMock()}):

        mock_fetch.return_value = None
        mock_build.return_value = {"model_status": "trained", "regime": {"regime": "BULL"}}
        
        mock_session = AsyncMock()
        mock_inst_result = MagicMock()
        mock_inst_result.scalars().first.return_value = MagicMock(id=1)
        mock_bars_result = MagicMock()
        mock_bars_result.scalars().all.return_value = [mock_bar] * 100
        mock_session.execute.side_effect = [mock_inst_result, mock_bars_result]
        mock_db_factory.return_value.__aenter__.return_value = mock_session

        res = await get_full_prediction("TEST")
        assert res["symbol"] == "TEST"

@pytest.mark.asyncio
async def test_get_full_prediction_cached():
    from app.services.prediction_engine import _in_memory_prediction_cache
    _in_memory_prediction_cache["prediction_raw:TEST"] = ({"cached": "yes"}, datetime.now(UTC).timestamp())
    with patch("app.services.market_data_service.MarketDataService._normalize_symbol", return_value="TEST"):
        res = await get_full_prediction("TEST")
        assert res == {"cached": "yes"}

@pytest.mark.asyncio
async def test_get_full_prediction_error():
    with patch("app.services.market_data_service.MarketDataService._normalize_symbol", return_value="TEST"), \
         patch("app.database.connection.async_session_factory", new_callable=MagicMock) as mock_db_factory:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Fetch error")
        mock_db_factory.return_value.__aenter__.return_value = mock_session
        with pytest.raises(ValueError):
            await get_full_prediction("TEST", bypass_cache=True)


def teardown_module(module):
    from app.services import prediction_engine
    from tests.conftest import mock_get_full_prediction
    prediction_engine.get_full_prediction = mock_get_full_prediction

