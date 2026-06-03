from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.journal import router as journal_router

app = FastAPI()
app.include_router(journal_router, prefix="/api/v1")
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
