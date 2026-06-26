import uuid
from decimal import Decimal
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import Select
from app.api.v1.portfolio import router as portfolio_router
from app.core.dependencies import get_db
import app.database.mongodb as mongodb_module
from app.core.config import get_settings

# Force MONGODB_URL to be set in settings
get_settings().MONGODB_URL = "mongodb://mock"

# In-memory mock DB for portfolio
in_memory_portfolio = {
    "cash_balance": 1000000.0,
    "holdings": []
}
in_memory_transactions = []

async def mock_mongo_get_portfolio(user_id):
    return in_memory_portfolio

async def mock_mongo_save_portfolio(user_id, cash, holdings):
    in_memory_portfolio["cash_balance"] = cash
    in_memory_portfolio["holdings"] = holdings
    return True

async def mock_mongo_add_transaction(user_id, symbol, tx_type, qty, price, net_amount):
    tx = {
        "transaction_id": str(uuid.uuid4()),
        "symbol": symbol,
        "type": tx_type,
        "quantity": qty,
        "price": price,
        "net_amount": net_amount,
        "timestamp": datetime.now(UTC).isoformat()
    }
    in_memory_transactions.append(tx)
    return tx

async def mock_get_live_price(symbol):
    return 2521.30

# Inject mocks
mongodb_module.mongo_get_portfolio = mock_mongo_get_portfolio
mongodb_module.mongo_save_portfolio = mock_mongo_save_portfolio
mongodb_module.mongo_add_transaction = mock_mongo_add_transaction
mongodb_module.get_live_price = mock_get_live_price


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
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(UTC)
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = datetime.now(UTC)
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
            
            if entity.__name__ == "Symbol":
                try:
                    params = statement.compile().params
                    tickers = [str(v) for k, v in params.items()]
                except Exception:
                    tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "AAPL", "MSFT"]
                from app.models.asset import Symbol
                symbols = []
                for t in tickers:
                    sym = Symbol(ticker=t)
                    sym.id = uuid.uuid5(uuid.NAMESPACE_DNS, t)
                    symbols.append(sym)
                class Result:
                    def scalars(self):
                        class Scalars:
                            def all(self):
                                return symbols
                        return Scalars()
                return Result()

            objs = [v for v in self.store.values() if isinstance(v, entity)]
            
            try:
                params = statement.compile().params
                for k, v in params.items():
                    if k.startswith("user_id"):
                        objs = [x for x in objs if getattr(x, "user_id", None) == uuid.UUID(str(v))]
                    elif k == "id" or k.startswith("id_"):
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
app.include_router(portfolio_router, prefix="/api/v1/portfolio")

shared_store = {}

async def override_get_db():
    yield InMemorySession(shared_store)

app.dependency_overrides[get_db] = override_get_db

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
