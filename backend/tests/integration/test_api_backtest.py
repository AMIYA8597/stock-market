from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.backtest import router as backtest_router

app = FastAPI()
app.include_router(backtest_router, prefix="/api/v1")
client = TestClient(app)


def test_run_status_and_results_flow() -> None:
    """Test complete backtest pipeline synchronously using Starlette TestClient."""
    # 1. Post a new backtest run
    payload = {
        "strategy_name": "ml_alpha",
        "strategy_params": {
            "commission_pct": 0.001,
            "slippage_pct": 0.0005,
            "benchmark": "^NSEI"
        },
        "universe": ["AAPL", "MSFT"],
        "date_from": "2025-06-03",
        "date_to": "2026-06-03",
        "initial_capital": 1000000.00
    }
    
    response = client.post("/api/v1/backtest/run", json=payload)
    assert response.status_code == 202
    job_info = response.json()
    assert "job_id" in job_info
    assert job_info["status"] == "PENDING"
    assert job_info["strategy_name"] == "ml_alpha"
    
    job_id = job_info["job_id"]
    
    # 2. Query status
    # TestClient processes FastAPI BackgroundTasks synchronously before returning,
    # so the job will already be in COMPLETED status.
    status_resp = client.get(f"/api/v1/backtest/status/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert "result_preview" in status_data
    assert status_data["result_preview"]["sharpe"] is not None
    assert status_data["result_preview"]["max_drawdown"] is not None
    
    # 3. Retrieve results
    results_resp = client.get(f"/api/v1/backtest/results/{job_id}")
    assert results_resp.status_code == 200
    results = results_resp.json()
    assert results["job_id"] == job_id
    assert results["strategy_name"] == "ml_alpha"
    assert results["status"] == "DONE"
    assert len(results["equity_curve"]) > 0
    assert len(results["drawdown_series"]) > 0
    assert "metrics" in results
    assert "walk_forward" in results
    assert "monte_carlo" in results
    assert "statistical_tests" in results
