from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.websocket.router import router as ws_router

app = FastAPI()
app.include_router(ws_router)
client = TestClient(app)


def test_ws_prices_subscription() -> None:
    with client.websocket_connect("/ws/prices") as websocket:
        websocket.send_json({"action": "subscribe", "symbols": ["RELIANCE.NS"]})
        payload = websocket.receive_json()
        assert payload["type"] == "tick"
        assert payload["symbol"] == "RELIANCE.NS"


def test_ws_signals_subscription() -> None:
    with client.websocket_connect("/ws/signals") as websocket:
        websocket.send_json({"action": "subscribe", "symbols": ["RELIANCE.NS"]})
        payload = websocket.receive_json()
        assert payload["type"] == "signal_update"
        assert payload["symbol"] == "RELIANCE.NS"
