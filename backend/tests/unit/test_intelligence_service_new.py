import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.intelligence_service import IntelligenceService
from app.schemas.intelligence import CounterfactualRequest

@pytest.fixture
def service():
    return IntelligenceService()

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_signal_success(mock_gfp, service):
    mock_gfp.return_value = {
        "is_computed": True,
        "ensemble": {
            "raw_ensemble": 0.5,
            "confidence": 0.8,
            "direction": "BUY",
            "kelly": 0.1,
            "momentum": {"vol_21d": 0.02},
            "regime": {"regime_variance": 0.015, "regime": "BULL", "bull_prob": 0.6, "bear_prob": 0.2},
            "xgboost": {"xgb_score": 0.4, "top_features": []}
        },
        "forecast": [{"horizon_days": 1, "predicted_price": 105, "prediction_low": 102, "prediction_high": 108}],
        "current_price": 100.0
    }
    res = service.get_signal("AAPL")
    assert res.symbol == "AAPL"
    assert res.ensemble.signal == "STRONG_BUY"
    assert res.ensemble.direction == "BUY"

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_signal_fallback(mock_gfp, service):
    mock_gfp.return_value = {"is_computed": False}
    res = service.get_signal("AAPL")
    assert res.is_fallback is True
    assert res.ensemble.signal == "NEUTRAL"

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_signal_exception(mock_gfp, service):
    mock_gfp.side_effect = Exception("error")
    res = service.get_signal("AAPL")
    assert res.is_fallback is True

def test_get_bulk_signals(service):
    with patch('app.services.intelligence_service.IntelligenceService.get_signal') as mock_gs:
        mock_gs.return_value = MagicMock()
        res = service.get_bulk_signals(["AAPL", "GOOG"])
        assert len(res) == 2
        assert mock_gs.call_count == 2

@patch('app.services.intelligence_service.MarketDataService.get_history', new_callable=AsyncMock)
def test_get_signal_history(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = service.get_signal_history("AAPL", "tft", 2)
    assert len(res) == 2
    assert res[0].model == "tft"

@patch('app.services.intelligence_service.MarketDataService.get_history', new_callable=AsyncMock)
def test_get_signal_history_exception(mock_history, service):
    mock_history.side_effect = Exception("error")
    res = service.get_signal_history("AAPL", "tft", 2)
    assert len(res) == 2

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_regime_current(mock_gfp, service):
    mock_gfp.return_value = {
        "ensemble": {
            "regime": {
                "regime": "BULL",
                "probs": {"BULL": 0.8, "BEAR": 0.1, "SIDEWAYS": 0.1},
                "regime_variance": 0.02
            }
        }
    }
    res = service.get_regime_current()
    assert res.state == "BULL"

@patch('app.services.intelligence_service.MarketDataService.get_history', new_callable=AsyncMock)
def test_get_regime_history(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = service.get_regime_history(2)
    assert len(res) == 2

def test_get_regime_statistics(service):
    res = service.get_regime_statistics()
    assert len(res) == 4

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_shap(mock_gfp, service):
    mock_gfp.return_value = {
        "ensemble": {
            "xgboost": {
                "top_features": [{"name": "feat1", "shap_value": 0.5}]
            }
        }
    }
    res = service.get_shap("AAPL")
    assert len(res.feature_contributions) == 1
    assert res.feature_contributions[0].name == "feat1"

@patch('app.services.intelligence_service.get_full_prediction', new_callable=AsyncMock)
def test_get_attention(mock_gfp, service):
    mock_gfp.return_value = {
        "lstm_attn": {
            "attention_peaks": [
                {"date": "2024-01-01", "weight": 0.8},
                {"date": "2024-01-02", "weight": 0.2}
            ]
        }
    }
    res = service.get_attention("AAPL", "lstm_attn")
    assert len(res.mean_weights) == 2

def test_get_counterfactuals(service):
    # Just checking empty return or basic since complex logic needs file paths
    req = CounterfactualRequest(target_direction="BUY", num_cfs=1)
    res = service.get_counterfactuals("AAPL", req)
    assert isinstance(res, list)

@patch('sqlite3.connect')
@patch('app.core.config.get_settings')
def test_get_model_accuracy(mock_settings, mock_connect, service):
    mock_settings.return_value.SYNC_DATABASE_URL = "sqlite:///test.db"
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = {"accuracy": 0.8, "precision": 0.7, "recall": 0.75, "auc": 0.85}

    res = service.get_model_accuracy()
    assert len(res) > 0

@patch('sqlite3.connect')
@patch('app.core.config.get_settings')
def test_get_drift(mock_settings, mock_connect, service):
    mock_settings.return_value.SYNC_DATABASE_URL = "sqlite:///test.db"
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    # simulate history length >= 10
    mock_cur.fetchall.return_value = [{"accuracy": 0.9}] * 5 + [{"accuracy": 0.5}] * 5

    res = service.get_drift()
    assert len(res) > 0

@patch('sqlite3.connect')
@patch('app.core.config.get_settings')
def test_get_ensemble_weights_history(mock_settings, mock_connect, service):
    mock_settings.return_value.SYNC_DATABASE_URL = "sqlite:///test.db"
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = [{"accuracy": 0.8, "created_at": "2024-01-01T00:00:00"}]

    res = service.get_ensemble_weights_history(5)
    assert len(res) > 0

def test_get_economic_calendar(service):
    assert service.get_economic_calendar() == []

@patch('app.services.intelligence_service.MarketDataService.get_history', new_callable=AsyncMock)
def test_get_correlation_graph(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = service.get_correlation_graph()
    assert res is not None

@patch('app.services.intelligence_service.MarketDataService.get_history', new_callable=AsyncMock)
def test_get_factor_exposure(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
        {"time": "2024-01-04T00:00:00", "close": 108},
        {"time": "2024-01-05T00:00:00", "close": 112},
    ] * 2  # Make sure len >= 10
    res = service.get_factor_exposure("AAPL")
    assert res is not None
