import uuid
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import Select
from app.api.v1.journal import router as journal_router
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
            objs = [v for v in self.store.values() if isinstance(v, entity)]
            
            # Precise filtering by id and user_id
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
app.include_router(journal_router, prefix="/api/v1")

shared_store = {}

async def override_get_db():
    yield InMemorySession(shared_store)

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_journal_flow() -> None:
    # 1. Create a trade journal entry
    payload = {
        "symbol": "AAPL",
        "notes": "Testing trade journal notes",
        "tags": "breakout,reversal",
        "rating": 5,
        "entry_price": 150.50,
        "exit_price": 155.00,
        "quantity": 10,
        "direction": "LONG"
    }
    response = client.post("/api/v1/journal", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["notes"] == "Testing trade journal notes"
    assert data["rating"] == 5
    assert float(data["entry_price"]) == 150.50
    journal_id = data["id"]

    # 2. Get all journal entries
    response = client.get("/api/v1/journal")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 1
    assert any(e["id"] == journal_id for e in entries)

    # 3. Delete the journal entry
    response = client.delete(f"/api/v1/journal/{journal_id}")
    assert response.status_code == 204

    # 4. Try deleting it again (should fail with 404)
    response = client.delete(f"/api/v1/journal/{journal_id}")
    assert response.status_code == 404
