from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router


app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
client = TestClient(app)


def test_payments_methods_and_balance_contracts() -> None:
    methods = client.get("/api/v1/payments/methods")
    assert methods.status_code == 200
    payload = methods.json()
    assert "methods" in payload
    assert len(payload["methods"]) >= 1

    balance = client.get("/api/v1/payments/balance")
    assert balance.status_code == 200
    balance_payload = balance.json()
    assert balance_payload["currency"] == "INR"
    assert "wallet_balance" in balance_payload


def test_payments_intent_confirm_and_history() -> None:
    create = client.post(
        "/api/v1/payments/intents",
        json={
            "amount": 7500,
            "currency": "INR",
            "method": "CARD",
            "description": "Top up",
        },
    )
    assert create.status_code == 200
    created_payload = create.json()
    assert created_payload["status"] == "requires_confirmation"

    confirm = client.post(
        "/api/v1/payments/confirm",
        json={
            "intent_id": created_payload["intent_id"],
            "confirmation_code": "123456",
        },
    )
    assert confirm.status_code == 200
    confirm_payload = confirm.json()
    assert confirm_payload["status"] == "succeeded"
    assert float(confirm_payload["credited_amount"]) == 7500.0

    history = client.get("/api/v1/payments/history?limit=10")
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] >= 1
    assert len(history_payload["items"]) >= 1
