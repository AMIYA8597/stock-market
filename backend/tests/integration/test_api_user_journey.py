from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router


app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
client = TestClient(app)


def test_core_api_user_journey_flow() -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "trader@example.com",
            "password": "S3curePass!123",
            "full_name": "Quant Trader",
        },
    )
    assert register.status_code == 201
    register_payload = register.json()
    assert register_payload["email"] == "trader@example.com"
    assert "id" in register_payload

    token = client.post(
        "/api/v1/auth/token",
        json={"email": "trader@example.com", "password": "S3curePass!123"},
    )
    assert token.status_code == 200
    token_payload = token.json()
    assert "access_token" in token_payload

    quote = client.get("/api/v1/market/quote/RELIANCE.NS")
    assert quote.status_code == 200
    quote_payload = quote.json()
    assert quote_payload["ticker"] == "RELIANCE.NS"
    assert "regime" in quote_payload

    signal = client.get("/api/v1/signals/RELIANCE.NS")
    assert signal.status_code == 200
    signal_payload = signal.json()
    assert signal_payload["symbol"] == "RELIANCE.NS"
    assert signal_payload["ensemble"]["direction"] in {"BUY", "SELL", "NEUTRAL", "STRONG_BUY", "STRONG_SELL"}

    order = client.post(
        "/api/v1/portfolio/transaction",
        json={
            "symbol": "RELIANCE.NS",
            "type": "BUY",
            "quantity": 10,
            "price": 2500,
        },
    )
    assert order.status_code == 200
    order_payload = order.json()
    assert order_payload["symbol"] == "RELIANCE.NS"
    assert order_payload["type"] == "BUY"

    holdings = client.get("/api/v1/portfolio/holdings")
    assert holdings.status_code == 200
    holdings_payload = holdings.json()
    assert "holdings" in holdings_payload
    assert "portfolio_value" in holdings_payload

    monitor = client.get("/api/v1/monitor/model-accuracy")
    assert monitor.status_code == 200
    monitor_payload = monitor.json()
    assert "models" in monitor_payload
    assert len(monitor_payload["models"]) >= 1
