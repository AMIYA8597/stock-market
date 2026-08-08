import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import Select

import app.api.v1.backtest as backtest_module
from app.api.v1.backtest import router as backtest_router
from app.core.dependencies import get_current_user, get_current_user_or_none, get_db
from app.models.payment import Subscription
from app.models.user import User


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

            # Simple filtering by id and user_id
            try:
                params = statement.compile().params
                for k, v in params.items():
                    if "user_id" in k:
                        objs = [x for x in objs if getattr(x, "user_id", None) == uuid.UUID(str(v))]
                    elif "id" in k or k == "id_1" or k == "id":
                        # Only apply this if it's not a status array or similar
                        if isinstance(v, (str, uuid.UUID)):
                            try:
                                objs = [x for x in objs if getattr(x, "id", None) == uuid.UUID(str(v))]
                            except Exception:
                                pass
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

async def override_get_current_user():
    return User(id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"))

app.dependency_overrides[get_current_user_or_none] = override_get_current_user
app.dependency_overrides[get_current_user] = override_get_current_user

# Pre-seed a subscription for the premium check
sub = Subscription(
    id=uuid.uuid4(),
    user_id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"),
    status="active",
)
shared_store[sub.id] = sub
backtest_module.async_session_factory = lambda: InMemorySession(shared_store)

client = TestClient(app)





def test_run_status_and_results_flow() -> None:
    """Test the backtest POST endpoint returns 202 + PENDING, and status endpoint works.

    The Celery task dispatch is mocked out since no broker is available in tests.
    This validates the API contract: POST -> 202 with job_id, GET status -> 200.
    """

    # 1. Post a new backtest run (mock Celery dispatch)
    with patch("app.api.v1.backtest.run_backtest_job_task.delay") as mock_delay:
        response = client.post(
            "/api/v1/backtest/run",
            json={
                "strategy_name": "ml_alpha",
                "strategy_params": {"commission_pct": 0.001},
                "universe": ["AAPL", "MSFT"],
                "date_from": "2025-06-03",
                "date_to": "2025-08-01",
                "initial_capital": 1000000.00,
            },
        )
        assert response.status_code == 202
        job_info = response.json()
        assert "job_id" in job_info
        assert job_info["status"] == "PENDING"
        assert job_info["strategy_name"] == "ml_alpha"
        assert job_info["universe_size"] == 2
        assert mock_delay.called  # Celery task was dispatched

        job_id = job_info["job_id"]

    # 2. Query status — should be PENDING since we mocked the Celery dispatch
    status_resp = client.get(f"/api/v1/backtest/status/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ("PENDING", "RUNNING")

    # 3. Results should 400 since job not completed
    results_resp = client.get(f"/api/v1/backtest/results/{job_id}")
    assert results_resp.status_code == 400


def test_backtest_engine_unit() -> None:
    """Unit test: EventDrivenBacktester produces valid metrics on synthetic data."""
    import numpy as np

    from research.backtesting.analytics import cagr, max_drawdown, sharpe_ratio, trade_metrics
    from research.backtesting.engine import EventDrivenBacktester

    n = 100
    prices = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    prices = np.maximum(prices, 10.0)  # prevent negative prices
    signals = np.where(np.arange(n) % 10 < 5, 1.0, -1.0)
    dates = np.array([f"2025-{(i//30)+1:02d}-{(i%28)+1:02d}" for i in range(n)])

    bt = EventDrivenBacktester(
        prices=prices, signals=signals, dates=dates,
        initial_capital=100000.0, target_vol=0.15
    )
    result = bt.run()

    assert len(result.equity_curve) == n
    assert len(result.daily_returns) == n
    assert result.equity_curve[0] == 100000.0

    # Metrics should be finite numbers
    c = cagr(result.equity_curve)
    s = sharpe_ratio(result.daily_returns)
    dd, dd_dur = max_drawdown(result.equity_curve)
    wr, pf, exp = trade_metrics(result.pnl)

    assert np.isfinite(c)
    assert np.isfinite(s)
    assert dd <= 0  # drawdown is negative or zero
    assert 0 <= wr <= 1

