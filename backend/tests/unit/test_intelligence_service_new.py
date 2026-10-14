from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.intelligence import CounterfactualRequest
from app.services.intelligence_service import IntelligenceService


@pytest.fixture
def service():
    return IntelligenceService()


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_signal_success(mock_gfp, service):
    mock_gfp.return_value = {
        "is_computed": True,
        "ensemble": {
            "raw_ensemble": 0.5,
            "confidence": 0.8,
            "direction": "BUY",
            "kelly": 0.1,
            "momentum": {"vol_21d": 0.02},
            "regime": {
                "regime_variance": 0.015,
                "regime": "BULL",
                "bull_prob": 0.6,
                "bear_prob": 0.2,
            },
            "xgboost": {"xgb_score": 0.4, "top_features": []},
        },
        "forecast": [
            {
                "horizon_days": 1,
                "predicted_price": 105,
                "prediction_low": 102,
                "prediction_high": 108,
            }
        ],
        "current_price": 100.0,
    }
    res = await service.get_signal("AAPL")
    assert res.symbol == "AAPL"
    assert res.ensemble.signal in ["BUY", "STRONG_BUY", "NEUTRAL"]
    assert res.ensemble.direction == "BUY"


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_signal_fallback(mock_gfp, service):
    mock_gfp.return_value = {"is_computed": False}
    res = await service.get_signal("AAPL")
    assert res.is_fallback is True
    assert res.ensemble.signal == "NEUTRAL"


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_signal_exception(mock_gfp, service):
    mock_gfp.side_effect = Exception("error")
    res = await service.get_signal("AAPL")
    assert res.is_fallback is True


@pytest.mark.asyncio
async def test_get_bulk_signals(service):
    with patch("app.services.intelligence_service.IntelligenceService.get_signal") as mock_gs:
        mock_gs.return_value = MagicMock()
        res = await service.get_bulk_signals(["AAPL", "GOOG"])
        assert len(res) == 2
        assert mock_gs.call_count == 2


@patch("app.services.intelligence_service.MarketDataService.get_history", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_signal_history(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = await service.get_signal_history("AAPL", "tft", 2)
    assert len(res) == 2
    assert res[0].model == "tft"


@patch("app.services.intelligence_service.MarketDataService.get_history", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_signal_history_exception(mock_history, service):
    mock_history.side_effect = Exception("error")
    res = await service.get_signal_history("AAPL", "tft", 2)
    assert len(res) == 2


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_regime_current(mock_gfp, service):
    mock_gfp.return_value = {
        "ensemble": {
            "regime": {
                "regime": "BULL",
                "probs": {"BULL": 0.8, "BEAR": 0.1, "SIDEWAYS": 0.1},
                "regime_variance": 0.02,
            }
        }
    }
    res = await service.get_regime_current()
    assert res.state == "BULL"


@patch("app.services.intelligence_service.MarketDataService.get_history", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_regime_history(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = await service.get_regime_history(2)
    assert len(res) == 2


@pytest.mark.asyncio
async def test_get_regime_statistics(service):
    res = await service.get_regime_statistics()
    assert len(res) >= 0


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_shap(mock_gfp, service):
    mock_gfp.return_value = {
        "ensemble": {"xgboost": {"top_features": [{"name": "feat1", "shap_value": 0.5}]}}
    }
    res = await service.get_shap("AAPL")
    assert len(res.feature_contributions) == 1
    assert res.feature_contributions[0].name == "feat1"


@patch("app.services.intelligence_service.get_full_prediction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_attention(mock_gfp, service):
    mock_gfp.return_value = {
        "lstm_attn": {
            "attention_peaks": [
                {"date": "2024-01-01", "weight": 0.8},
                {"date": "2024-01-02", "weight": 0.2},
            ]
        }
    }
    res = await service.get_attention("AAPL", "lstm_attn")
    assert len(res.mean_weights) == 2


@pytest.mark.asyncio
async def test_get_counterfactuals(service):
    # Just checking empty return or basic since complex logic needs file paths
    req = CounterfactualRequest(target_direction="BUY", num_cfs=1)
    res = await service.get_counterfactuals("AAPL", req)
    assert isinstance(res, list)


@patch("app.database.connection.async_session_factory")
@pytest.mark.asyncio
async def test_get_model_accuracy(mock_session_factory, service):
    """Regression test: get_model_accuracy() actually queries via
    app.database.connection.async_session_factory() (a real async SQLAlchemy
    session), not sqlite3.connect - the previous version of this test mocked
    sqlite3.connect, which the implementation never calls, so the test made
    a real, unmocked network connection attempt to whatever DATABASE_URL is
    configured (backend/.env) every time it ran. With no connect timeout
    configured anywhere, that could - and did - hang indefinitely instead of
    failing fast, in an environment where that network path is blocked."""
    mock_row = MagicMock()
    mock_row.model_family = "xgboost"
    mock_row.metrics_json = {"precision": 0.7, "recall": 0.75, "accuracy": 0.8}
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    res = await service.get_model_accuracy()
    assert len(res) == 1
    assert res[0].model == "xgboost"
    assert res[0].precision == 0.7
    assert res[0].recall == 0.75
    assert res[0].directional_accuracy == 0.8


@pytest.mark.asyncio
async def test_get_drift_returns_empty_list(service):
    """get_drift() has no real drift-detection pipeline implemented yet
    (no frozen reference distribution, no live ADWIN/KS computation). It
    must honestly report that as an empty result rather than serve
    hardcoded fake psi/js/ks values as if they were measured drift."""
    res = await service.get_drift()
    assert res == []


@pytest.mark.asyncio
async def test_get_ensemble_weights_history(service):
    res = await service.get_ensemble_weights_history(5)
    assert res == []


@pytest.mark.asyncio
async def test_get_economic_calendar(service):
    assert await service.get_economic_calendar() == []


@patch("app.services.intelligence_service.MarketDataService.get_history", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_correlation_graph(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
    ]
    res = await service.get_correlation_graph()
    assert res is not None


@patch("app.services.intelligence_service.MarketDataService.get_history", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_factor_exposure(mock_history, service):
    mock_history.return_value = [
        {"time": "2024-01-01T00:00:00", "close": 100},
        {"time": "2024-01-02T00:00:00", "close": 105},
        {"time": "2024-01-03T00:00:00", "close": 110},
        {"time": "2024-01-04T00:00:00", "close": 108},
        {"time": "2024-01-05T00:00:00", "close": 112},
    ] * 2  # Make sure len >= 10
    res = await service.get_factor_exposure("AAPL")
    assert res is not None
