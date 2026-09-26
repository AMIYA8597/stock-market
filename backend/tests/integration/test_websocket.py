from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.websocket.router import router as ws_router

app = FastAPI()
app.include_router(ws_router)
client = TestClient(app)


from unittest.mock import AsyncMock, patch


def test_ws_prices_subscription() -> None:
    # get_quote() queries the canonical PostgreSQL database directly (real DB, no
    # cache). Leaving it unmocked makes this test's outcome depend on live network
    # latency to that database racing the connection manager's 30s heartbeat loop:
    # fast under an isolated run, but flaky under full-suite connection-pool
    # pressure. Mock it so the test verifies the websocket subscribe -> tick
    # contract deterministically, independent of live DB reachability/latency.
    fake_quote = {
        "symbol": "RELIANCE.NS",
        "price": 2845.20,
        "change": 12.5,
        "change_pct": 0.44,
        "source": "test-fixture",
    }
    with (
        patch("app.websocket.ws_auth.authenticate_ws") as mock_auth,
        patch(
            "app.services.market_data_service.MarketDataService.get_quote",
            new=AsyncMock(return_value=fake_quote),
        ),
    ):
        mock_auth.return_value = "user-123"
        with client.websocket_connect("/ws/prices") as websocket:
            websocket.send_json({"action": "subscribe", "symbols": ["RELIANCE.NS"]})
            payload = websocket.receive_json()
            assert payload["type"] == "tick"
            assert payload["symbol"] == "RELIANCE.NS"


def test_ws_signals_subscription() -> None:
    with patch("app.websocket.ws_auth.authenticate_ws") as mock_auth:
        mock_auth.return_value = "user-123"
        with client.websocket_connect("/ws/signals") as websocket:
            websocket.send_json({"action": "subscribe", "symbols": ["RELIANCE.NS"]})
            payload = websocket.receive_json()
            assert payload["type"] == "signal"
            assert payload["symbol"] == "RELIANCE.NS"
