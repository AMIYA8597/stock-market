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
    # autospec=True is required so mocked async methods (get_signal,
    # get_regime_current, ...) become AsyncMock instead of a plain
    # MagicMock; without it `await mock_service.get_signal(...)` raises
    # "object dict can't be used in 'await' expression" against every
    # endpoint below, since the real IntelligenceService methods are async.
    with patch("app.api.v1.intelligence.intelligence_service", autospec=True) as mock_service:
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
        yield mock_service

def test_signals_single_and_bulk() -> None:
    single = client.get("/api/v1/signals/RELIANCE.NS")
    bulk = client.get("/api/v1/signals/bulk", params={"symbols": "RELIANCE.NS,TCS.NS"})
    assert single.status_code == 200
    assert bulk.status_code == 200
    assert single.json()["symbol"] == "RELIANCE.NS"
    assert len(bulk.json()) == 2


def test_regime_endpoints() -> None:
    # /regime/statistics, /explain/*, and /monitor/* used to be defined a
    # second time on this router, duplicating market.py/regime.py/
    # explain.py/models.py; those duplicates were permanently unreachable
    # dead code in the real app (which mounts those dedicated routers
    # first) and have been removed from intelligence.py. This test now
    # only covers the two regime paths that are genuinely this router's
    # responsibility (see api/v1/router.py and the KT doc's "Where to
    # Change What" table for /regime/statistics, /explain/*, /monitor/*).
    current = client.get("/api/v1/regime/current")
    history = client.get("/api/v1/regime/history", params={"days": 252})
    assert current.status_code == 200
    assert history.status_code == 200
    assert "state" in current.json()
    assert len(history.json()) >= 30
