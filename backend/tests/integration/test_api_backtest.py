import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import Select
from app.api.v1.backtest import router as backtest_router
import app.api.v1.backtest as backtest_module
from app.core.dependencies import get_db

class InMemorySession:
    def __init__(self, store=None):
        self.store = store if store is not None else {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def add(self, obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        self.store[obj.id] = obj

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def delete(self, obj):
        if hasattr(obj, "id") and obj.id in self.store:
            del self.store[obj.id]

    async def execute(self, statement, *args, **kwargs):
        if isinstance(statement, Select):
            entity = statement.column_descriptions[0]["entity"]
            objs = [v for v in self.store.values() if isinstance(v, entity)]
            
            # Simple filtering by id
            try:
                params = statement.compile().params
                for k, v in params.items():
                    if "id" in k or k == "id_1" or k == "id":
                        objs = [x for x in objs if getattr(x, "id", None) == uuid.UUID(str(v))]
            except Exception:
                pass

            class Result:
                def __init__(self, items):
                    self.items = items
                def scalar_one_or_none(self):
                    return self.items[0] if self.items else None
                def scalar_one(self):
                    return self.items[0]
                def scalars(self):
                    class Scalars:
                        def __init__(self, items):
                            self.items = items
                        def all(self):
                            return self.items
                        def first(self):
                            return self.items[0] if self.items else None
                    return Scalars(self.items)
                def all(self):
                    return self.items
            return Result(objs)

        class DummyResult:
            def scalar_one_or_none(self):
                return None
            def scalar_one(self):
                return None
            def scalars(self):
                return self
            def all(self):
                return []
        return DummyResult()

app = FastAPI()
app.include_router(backtest_router, prefix="/api/v1")

shared_store = {}

async def override_get_db():
    yield InMemorySession(shared_store)

app.dependency_overrides[get_db] = override_get_db
backtest_module.async_session_factory = lambda: InMemorySession(shared_store)

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
