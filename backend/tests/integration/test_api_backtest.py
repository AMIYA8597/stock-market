import uuid
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

def _mock_require_feature(feature_key: str):
    async def _dependency():
        return {"organization_id": uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"), "sub": "3b79b787-f2a8-4a48-abf1-0268d6131a5b"}
    return _dependency

with patch("app.api.v1.backtest.require_feature", _mock_require_feature):
    import app.api.v1.backtest as backtest_module
    from app.api.v1.backtest import router as backtest_router
    from app.core.dependencies import get_current_user, get_current_user_or_none, get_db

class InMemorySession:
    def __init__(self, store=None):
        self.store = store if store is not None else {}
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass
    def add(self, obj):
        if not getattr(obj, "id", None): obj.id = uuid.uuid4()
        self.store[obj.id] = obj
    async def flush(self): pass
    async def commit(self): pass
    async def refresh(self, obj): pass
    async def execute(self, statement, *args, **kwargs):
        from sqlalchemy.sql import Select
        if isinstance(statement, Select):
            entity = statement.column_descriptions[0]['entity']
            if getattr(entity, '__name__', '') == 'PlanEntitlement':
                class MockResult:
                    def scalars(self):
                        class MockScalars:
                            def first(self):
                                return True
                        return MockScalars()
                return MockResult()
        from sqlalchemy.sql import Select
        if isinstance(statement, Select):
            entity = statement.column_descriptions[0]["entity"]
            objs = [v for v in self.store.values() if isinstance(v, entity)]
            try:
                params = statement.compile().params
                for k, v in params.items():
                    if "user_id" in k:
                        objs = [x for x in objs if getattr(x, "user_id", None) == uuid.UUID(str(v))]
                    elif "id" in k or k == "id_1" or k == "id":
                        if isinstance(v, (str, uuid.UUID)):
                            try: objs = [x for x in objs if getattr(x, "id", None) == uuid.UUID(str(v))]
                            except Exception: pass
            except Exception: pass
            class MockResult:
                def __init__(self, items): self.items = items
                def scalar_one_or_none(self): return self.items[0] if self.items else None
                def scalars(self):
                    class MockScalars:
                        def __init__(self, it): self.it = it
                        def all(self): return self.it
                        def first(self): return self.it[0] if self.it else None
                    return MockScalars(self.items)
            return MockResult(objs)

app = FastAPI()
app.include_router(backtest_router, prefix="/api/v1")


shared_store = {}
from app.models.user import User
u = User(id=uuid.UUID('3b79b787-f2a8-4a48-abf1-0268d6131a5b'), email='test@test.com')
shared_store[u.id] = u


async def override_get_db():
    yield InMemorySession(shared_store)

app.dependency_overrides[get_db] = override_get_db

from app.models.user import User

from app.core.security import get_current_context, RequestContext
async def override_get_current_context():
    return RequestContext(
        user_id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"),
        organization_id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"),
        organization_role="OWNER"
    )
app.dependency_overrides[get_current_context] = override_get_current_context

async def override_get_current_user():

    return User(id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"))

app.dependency_overrides[get_current_user_or_none] = override_get_current_user
app.dependency_overrides[get_current_user] = override_get_current_user

backtest_module.async_session_factory = lambda: InMemorySession(shared_store)
client = TestClient(app)


# Strip dependencies from all routes to avoid 401s in this test
for route in backtest_router.routes:
    route.dependencies = []


# Dynamically find the require_feature dependency and override it
from app.api.v1.backtest import post_backtest_run
import inspect
sig = inspect.signature(post_backtest_run)
for param in sig.parameters.values():
    if hasattr(param.default, 'dependency') and param.default.dependency:
        dep = param.default.dependency
        if dep.__name__ == '_dependency' or 'require_feature' in str(dep):
            app.dependency_overrides[dep] = lambda: {'sub': '3b79b787-f2a8-4a48-abf1-0268d6131a5b'}

def test_run_status_and_results_flow() -> None:


    req = {
        "strategy_name": "TestStrategy",
        "universe": ["RELIANCE", "TCS"],
        "date_from": "2023-01-01",
        "date_to": "2023-01-10",
        "initial_capital": 100000.0,
    }
    with patch("app.api.v1.backtest.run_backtest_job_task") as mock_task:
        resp = client.post("/api/v1/backtest/run", json=req)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        mock_task.delay.assert_called_once_with(job_id)

    resp2 = client.get(f"/api/v1/backtest/status/{job_id}")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "PENDING"

    job = shared_store[uuid.UUID(job_id)]
    job.status = "DONE"
    job.progress = 100
    job.results = {
        "metrics": {
            "total_return": 10.5, 
            "cagr": 5.2, 
            "sharpe": 1.1,
            "max_drawdown": 0.1,
            "max_drawdown_duration_days": 5,
            "win_rate": 0.6,
            "avg_win": 1.5,
            "avg_loss": 1.0,
            "payoff_ratio": 1.5,
            "num_trades": 10,
            "gross_profit": 15.0,
            "gross_loss": 4.5,
            "sortino": 1.2,
            "calmar": 1.3,
            "omega": 1.4,
            "deflated_sharpe": 1.5
        },
        "equity_curve": [{"date": "2023-01-10", "portfolio_value": 110500}],
        "drawdown_series": [],
        "trade_log": [],
    }

    resp3 = client.get(f"/api/v1/backtest/results/{job_id}")
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["status"] == "DONE"
    assert data["metrics"]["total_return"] == "10.5"
