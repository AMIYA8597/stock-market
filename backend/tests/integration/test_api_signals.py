from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.intelligence import router as intelligence_router


app = FastAPI()
app.include_router(intelligence_router, prefix="/api/v1")
client = TestClient(app)


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
    cfs = client.post("/api/v1/explain/counterfactual/RELIANCE.NS", json={"target_direction": "BUY", "num_cfs": 3})
    accuracy = client.get("/api/v1/monitor/model-accuracy")
    drift = client.get("/api/v1/monitor/drift")
    weights = client.get("/api/v1/monitor/ensemble-weights-history", params={"days": 252})

    assert shap.status_code == 200
    assert attn.status_code == 200
    assert cfs.status_code == 200
    assert accuracy.status_code == 200
    assert drift.status_code == 200
    assert weights.status_code == 200
    assert len(cfs.json()) == 3
