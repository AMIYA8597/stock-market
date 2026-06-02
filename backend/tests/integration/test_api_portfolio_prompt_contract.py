from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.portfolio import router as portfolio_router

app = FastAPI()
app.include_router(portfolio_router, prefix="/api/v1/portfolio")
client = TestClient(app)


def test_prompt_portfolio_endpoints() -> None:
    holdings = client.get("/api/v1/portfolio/holdings")
    tx = client.post(
        "/api/v1/portfolio/transaction",
        json={"symbol": "RELIANCE.NS", "type": "BUY", "quantity": 10, "price": 2500},
    )
    perf = client.get("/api/v1/portfolio/performance")
    risk = client.get("/api/v1/portfolio/risk-metrics")
    optimize = client.post(
        "/api/v1/portfolio/optimize",
        json={
            "universe": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
            "method": "hrp",
            "constraints": {"max_weight": 0.2},
            "use_ml_views": True,
        },
    )

    assert holdings.status_code == 200
    assert tx.status_code == 200
    assert perf.status_code == 200
    assert risk.status_code == 200
    assert optimize.status_code == 200

    payload = optimize.json()
    assert "weights" in payload
    assert "efficient_frontier" in payload
    assert len(payload["efficient_frontier"]) == 100
