from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.market_data import router as market_router


app = FastAPI()
app.include_router(market_router, prefix="/api/v1/market")
client = TestClient(app)


def test_quote_contract_fields() -> None:
    response = client.get("/api/v1/market/quote/RELIANCE.NS")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        payload = response.json()
        assert payload["ticker"] == "RELIANCE.NS"
        assert "regime" in payload
        assert "signal" in payload


def test_history_contract() -> None:
    response = client.get("/api/v1/market/history/RELIANCE.NS", params={"interval": "1d", "period": "1y"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE.NS"
    assert payload["interval"] == "1d"
    assert len(payload["data"]) > 10


def test_indices_and_movers() -> None:
    indices = client.get("/api/v1/market/indices")
    movers = client.get("/api/v1/market/movers", params={"exchange": "NSE", "type": "gainers"})
    assert indices.status_code == 200
    assert movers.status_code == 200
    assert len(indices.json()) >= 6
    assert len(movers.json()) == 20


def test_heatmap_search_and_calendar() -> None:
    heatmap = client.get("/api/v1/market/heatmap", params={"exchange": "NSE", "metric": "return_1d"})
    search = client.get("/api/v1/market/search", params={"q": "REL"})
    calendar = client.get("/api/v1/market/economic-calendar")
    assert heatmap.status_code == 200
    assert search.status_code == 200
    assert calendar.status_code == 200
    assert len(search.json()) >= 1
