from fastapi import FastAPI
from fastapi.testclient import TestClient

from unittest.mock import patch
import pytest

from app.api.v1.intelligence import router as intelligence_router

app = FastAPI()
app.include_router(intelligence_router, prefix="/api/v1")
client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_intelligence_service():
    with patch("app.api.v1.intelligence.intelligence_service") as mock_service:
        signal = {
            "symbol": "RELIANCE.NS",
            "timestamp": "2023-01-01T00:00:00Z",
            "ensemble": {"signal": "BUY", "confidence": 0.8, "direction": "BUY", "kelly_fraction": 0.5},
            "models": {"xgboost": {"raw_signal": 0.8, "top_features": []}},
            "model_weights": {"xgboost": 1.0},
            "regime": {"state": "BULL", "probs": {}, "transition_probs": {}}
        }
        mock_service.get_signal.return_value = signal
        signal2 = signal.copy()
        signal2["symbol"] = "TCS.NS"
        mock_service.get_bulk_signals.return_value = [signal, signal2]
        mock_service.get_regime_current.return_value = {"state": "BULL", "probs": {}, "transition_matrix": [], "cond_vol_1d": 0, "cond_vol_5d": 0, "cond_vol_21d": 0, "days_in_state": 0, "last_transition_date": "2023-01-01"}
        mock_service.get_regime_history.return_value = [{"time": "2023-01-01", "state": "BULL", "probs": {}, "cond_vol": 0.0}] * 30
        mock_service.get_regime_statistics.return_value = []
        mock_service.get_model_accuracy.return_value = []
        mock_service.get_drift.return_value = []
        mock_service.get_ensemble_weights_history.return_value = []
        yield mock_service

def test_signals_single_and_bulk() -> None:
    single = client.get("/api/v1/signals/RELIANCE.NS")
    bulk = client.get("/api/v1/signals/bulk", params={"symbols": "RELIANCE.NS,TCS.NS"})
    assert single.status_code == 200
    assert bulk.status_code == 200
    assert single.json()["symbol"] == "RELIANCE.NS"
    assert len(bulk.json()) == 2


def test_regime_endpoints() -> None:
    current = client.get("/api/v1/regime/current")
    history = client.get("/api/v1/regime/history", params={"days": 252})
    stats = client.get("/api/v1/regime/statistics")
    assert current.status_code == 200
    assert history.status_code == 200
    assert stats.status_code == 200
    assert "state" in current.json()
    assert len(history.json()) >= 30


def test_explain_and_monitor_endpoints() -> None:
    shap = client.get("/api/v1/explain/shap/RELIANCE.NS")
    attn = client.get("/api/v1/explain/attention/RELIANCE.NS", params={"model": "tft"})
    cfs = client.post(
        "/api/v1/explain/counterfactual/RELIANCE.NS", json={"target_direction": "BUY", "num_cfs": 3}
    )
    accuracy = client.get("/api/v1/monitor/model-accuracy")
    drift = client.get("/api/v1/monitor/drift")
    weights = client.get("/api/v1/monitor/ensemble-weights-history", params={"days": 252})

    assert shap.status_code == 401
    assert attn.status_code == 401
    assert cfs.status_code == 401
    assert accuracy.status_code == 200
    assert drift.status_code == 200
    assert weights.status_code == 200
