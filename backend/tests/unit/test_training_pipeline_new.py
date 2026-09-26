import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.services.ml_engine.training_pipeline import TrainingPipeline


@pytest.fixture
def mock_db_session():
    with patch("app.services.ml_engine.training_pipeline.async_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        # Setup for first execute (select Instrument)
        mock_result = MagicMock()
        mock_instrument = MagicMock()
        mock_instrument.id = uuid.uuid4()
        mock_result.scalars.return_value.first.return_value = mock_instrument
        mock_session.execute.return_value = mock_result

        yield mock_session

@pytest.fixture
def dummy_data():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    df = pd.DataFrame({
        "Date": dates,
        "Open": np.random.rand(400) * 100,
        "High": np.random.rand(400) * 100,
        "Low": np.random.rand(400) * 100,
        "Close": np.random.rand(400) * 100,
        "Volume": np.random.randint(100, 1000, size=400),
    })
    df.set_index("Date", inplace=True)
    return df

@pytest.fixture
def feature_data():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    df = pd.DataFrame({
        "time": dates,
        "open": np.random.rand(400) * 100,
        "high": np.random.rand(400) * 100,
        "low": np.random.rand(400) * 100,
        "close": np.random.rand(400) * 100,
        "volume": np.random.randint(100, 1000, size=400),
        "target_return": np.random.randn(400) * 0.01,
        "target_direction": np.random.randint(0, 2, size=400),
        "target_direction_1d": np.random.randint(0, 2, size=400),
        "feature_1": np.random.randn(400),
        "feature_2": np.random.randn(400),
        "regime_label": ["bull"] * 200 + ["bear"] * 200
    })
    return df

def setup_mock_model(mock_class, has_predict_proba_batch=False, has_save=False):
    instance = mock_class.return_value
    instance.fit.return_value = None
    instance.predict_proba.return_value = np.random.rand(63, 2)
    instance.get_feature_importances.return_value = {"feature_1": 0.5, "feature_2": 0.5}

    if not has_predict_proba_batch:
        del instance.predict_proba_batch
    else:
        instance.predict_proba_batch.return_value = np.random.rand(63, 2)

    if not has_save:
        del instance.save

    return instance

@pytest.mark.asyncio
@patch("yfinance.Ticker")
@patch("app.services.ml_engine.training_pipeline.FeaturePipeline")
@patch("joblib.dump")
async def test_training_pipeline_success(
    mock_joblib_dump,
    mock_feature_pipeline_class,
    mock_ticker_class,
    mock_db_session,
    dummy_data,
    feature_data
):
    # Mock yfinance
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = dummy_data
    mock_ticker_class.return_value = mock_ticker_instance

    # Mock FeaturePipeline
    mock_feature_pipeline_instance = MagicMock()
    mock_feature_pipeline_instance.run.return_value = feature_data
    mock_feature_pipeline_class.return_value = mock_feature_pipeline_instance

    with patch("app.services.ml_engine.training_pipeline.NaiveDirectionalClassifier") as mock_naive, \
         patch("app.services.ml_engine.training_pipeline.ARIMADirectionalClassifier") as mock_arima, \
         patch("app.services.ml_engine.training_pipeline.XGBoostDirectionalClassifier") as mock_xgb, \
         patch("app.services.ml_engine.training_pipeline.LightGBMDirectionalClassifier") as mock_lgb, \
         patch("app.services.ml_engine.training_pipeline.LSTMAttentionClassifier") as mock_lstm, \
         patch("optuna.create_study") as mock_create_study:

        setup_mock_model(mock_naive)
        setup_mock_model(mock_arima)
        setup_mock_model(mock_xgb)
        setup_mock_model(mock_lgb)
        setup_mock_model(mock_lstm, has_save=True) # LSTM usually has save

        # Mock optuna
        mock_study = MagicMock()
        mock_study.best_params = {"max_depth": 3, "learning_rate": 0.1}
        mock_create_study.return_value = mock_study

        pipeline = TrainingPipeline("AAPL")
        with patch.object(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals() else pd.DataFrame()):
            results = await pipeline.run()

        assert isinstance(results, dict)
        assert "Naive" in results
        assert "XGBoost" in results
        assert "LSTM" in results

        # Best model could be any, if it's not LSTM, joblib dump might be called
        # Wait, if best model is LSTM, joblib won't be called.
        # Just check if session adds were called
        assert mock_db_session.add.call_count > 0
        assert mock_db_session.commit.called

@pytest.mark.asyncio
async def test_training_pipeline_instrument_not_found(mock_db_session):
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None
    pipeline = TrainingPipeline("UNKNOWN")

    with pytest.raises(ValueError, match="not found in DB"):
        await pipeline.run()

@pytest.mark.asyncio
@patch("yfinance.Ticker")
async def test_training_pipeline_insufficient_data(mock_ticker_class, mock_db_session):
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = pd.DataFrame()
    mock_ticker_class.return_value = mock_ticker_instance

    pipeline = TrainingPipeline("AAPL")
    with patch.object(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals() else pd.DataFrame()):
        results = await pipeline.run()
    assert results == {}

@pytest.mark.asyncio
@patch("yfinance.Ticker")
@patch("app.services.ml_engine.training_pipeline.FeaturePipeline")
async def test_training_pipeline_dropped_data(mock_feature_pipeline_class, mock_ticker_class, mock_db_session, dummy_data, feature_data):
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = dummy_data
    mock_ticker_class.return_value = mock_ticker_instance

    # The shared 400-row fixture can never drop below the 252-row minimum
    # while staying under the 10% high-NaN-column threshold (10% of 400 = 40
    # rows max, leaving 360 >> 252). Trim to 270 rows first so a <10% NaN
    # injection (25 rows, 9.3%) actually pushes the post-dropna count below
    # 252, exercising the intended "insufficient rows after dropna" path
    # instead of leaving it unreachable.
    feature_data = feature_data.iloc[:270].copy()
    feature_data.loc[:24, "open"] = np.nan

    mock_feature_pipeline_instance = MagicMock()
    mock_feature_pipeline_instance.run.return_value = feature_data
    mock_feature_pipeline_class.return_value = mock_feature_pipeline_instance

    pipeline = TrainingPipeline("AAPL")
    with patch.object(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals() else pd.DataFrame()):
        results = await pipeline.run()
    assert results == {}

@pytest.mark.asyncio
@patch("yfinance.Ticker")
@patch("app.services.ml_engine.training_pipeline.FeaturePipeline")
@patch("joblib.dump")
async def test_training_pipeline_honesty_law(
    mock_joblib_dump,
    mock_feature_pipeline_class,
    mock_ticker_class,
    mock_db_session,
    dummy_data,
    feature_data
):
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = dummy_data
    mock_ticker_class.return_value = mock_ticker_instance

    mock_feature_pipeline_instance = MagicMock()
    mock_feature_pipeline_instance.run.return_value = feature_data
    mock_feature_pipeline_class.return_value = mock_feature_pipeline_instance

    with patch("app.services.ml_engine.training_pipeline.NaiveDirectionalClassifier") as mock_naive, \
         patch("app.services.ml_engine.training_pipeline.ARIMADirectionalClassifier") as mock_arima, \
         patch("app.services.ml_engine.training_pipeline.XGBoostDirectionalClassifier") as mock_xgb, \
         patch("app.services.ml_engine.training_pipeline.LightGBMDirectionalClassifier") as mock_lgb, \
         patch("app.services.ml_engine.training_pipeline.LSTMAttentionClassifier") as mock_lstm, \
         patch("optuna.create_study") as mock_create_study:

        def mock_predict_proba(X_test):
            indices = X_test.index
            y_test = feature_data.loc[indices, "target_direction"]
            probs = np.zeros((len(X_test), 2))
            probs[:, 1] = y_test.values * 0.9 + 0.05
            probs[:, 0] = 1 - probs[:, 1]
            return probs

        for mock_model_class in [mock_naive, mock_arima, mock_xgb, mock_lgb, mock_lstm]:
            inst = setup_mock_model(mock_model_class)
            inst.predict_proba.side_effect = mock_predict_proba

        mock_study = MagicMock()
        mock_study.best_params = {"max_depth": 3, "learning_rate": 0.1}
        mock_create_study.return_value = mock_study

        pipeline = TrainingPipeline("AAPL")
        with patch.object(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals() else pd.DataFrame()):
            results = await pipeline.run()

        assert isinstance(results["Naive"]["accuracy"], float)
        assert isinstance(results["Naive"]["sharpe"], float)
