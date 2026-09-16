import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, UTC
import pandas as pd
import math
import json
import importlib

# Reload the module to bypass conftest.py global mocks
import app.services.market_data_service as mds_module
importlib.reload(mds_module)

from app.services.market_data_service import MarketDataService, HistoryList, safe_float, TokenBucket

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    mock.setex = AsyncMock()
    return mock

@pytest.fixture(autouse=True)
def reset_mds_state():
    MarketDataService._session = None
    MarketDataService._health_cache = None
    MarketDataService._in_memory_ticker_history_df_cache = {}
    MarketDataService._yfinance_bucket.tokens = MarketDataService._yfinance_bucket.capacity
    MarketDataService._nse_bucket.tokens = MarketDataService._nse_bucket.capacity
    yield

def test_safe_float():
    assert safe_float("123.45") == 123.45
    assert safe_float(float('nan')) == 0.0
    assert safe_float(float('inf')) == 0.0
    assert safe_float("invalid", 1.0) == 1.0

@pytest.mark.asyncio
async def test_token_bucket():
    bucket = TokenBucket(rate=100.0, capacity=2.0)
    await bucket.consume(1.0)
    assert bucket.tokens <= 1.0
    await asyncio.sleep(0.02)
    await bucket.consume(1.0)

@pytest.mark.asyncio
async def test_throttle_methods():
    await MarketDataService._throttle_yfinance("RELIANCE")
    await MarketDataService._throttle_nse()

def test_get_session():
    session1 = MarketDataService.get_session()
    session2 = MarketDataService.get_session()
    assert session1 is session2
    assert "User-Agent" in session1.headers

@pytest.mark.asyncio
async def test_health_ok():
    with patch("yfinance.download") as mock_yf:
        mock_yf.return_value = pd.DataFrame({"Close": [1]})
        res = await MarketDataService.health()
        assert res == {"status": "ok"}
        res2 = await MarketDataService.health()
        assert res2 == {"status": "ok"}

@pytest.mark.asyncio
async def test_health_fail():
    with patch("yfinance.download") as mock_yf:
        mock_yf.side_effect = Exception("error")
        res = await MarketDataService.health()
        assert res == {"status": "unhealthy"}

def test_normalize_symbol():
    assert MarketDataService._normalize_symbol("NIFTY50") == "^NSEI"
    assert MarketDataService._normalize_symbol("AAPL") == "AAPL"
    assert MarketDataService._normalize_symbol("RELIANCE") == "RELIANCE.NS"
    assert MarketDataService._normalize_symbol("RELIANCE.NS") == "RELIANCE.NS"
    assert MarketDataService._normalize_symbol("USDINR=X") == "USDINR=X"
    assert MarketDataService._normalize_symbol("CL=F") == "CL=F"

@pytest.mark.asyncio
async def test_get_batch_quotes():
    with patch.object(MarketDataService, "get_quote", side_effect=[{"price": 100}, Exception("error")]):
        res = await MarketDataService.get_batch_quotes(["RELIANCE", "INVALID"])
        assert res["RELIANCE"] == {"price": 100}
        assert res["INVALID"] is None

@pytest.mark.asyncio
async def test_get_quote_upstox_cache():
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote") as m:
        m.return_value = {"price": 100, "symbol": "RELIANCE.NS"}
        res = await MarketDataService.get_quote("RELIANCE")
        assert res["price"] == 100
        assert res["source"] == "NSE"

@pytest.mark.asyncio
async def test_get_quote_redis_cache(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            mock_redis.get.return_value = json.dumps({"price": 200, "source": "redis"})
            res = await MarketDataService.get_quote("RELIANCE")
            assert res["price"] == 200
            assert res["source"] == "redis"

@pytest.mark.asyncio
async def test_get_quote_redis_cache_error(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            mock_redis.get.return_value = json.dumps({"error": True})
            with pytest.raises(ValueError):
                await MarketDataService.get_quote("RELIANCE")

@pytest.mark.asyncio
async def test_get_quote_yfinance_success(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            with patch("yfinance.Ticker") as mock_ticker_cls:
                mock_ticker = MagicMock()
                mock_info = MagicMock()
                mock_info.last_price = 105.0
                mock_info.year_high = 150.0
                mock_info.year_low = 50.0
                mock_ticker.fast_info = mock_info
                mock_ticker.info = {"marketCap": 1000, "fiftyTwoWeekHigh": 120, "fiftyTwoWeekLow": 80}
                mock_ticker_cls.return_value = mock_ticker
                
                res = await MarketDataService.get_quote("RELIANCE")
                assert res["price"] == 105.0
                assert res["market_cap"] == 1000.0

@pytest.mark.asyncio
async def test_get_quote_yfinance_fallback_history(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            with patch("yfinance.Ticker") as mock_ticker_cls:
                mock_ticker = MagicMock()
                type(mock_ticker).fast_info = PropertyMock(side_effect=Exception("no fast info"))
                mock_ticker_cls.return_value = mock_ticker
                
                with patch.object(MarketDataService, "get_history", return_value=[
                    {"close": 100, "open": 90, "high": 110, "low": 80, "volume": 1000}, 
                    {"close": 105, "open": 95, "high": 115, "low": 85, "volume": 1100}
                ]):
                    res = await MarketDataService.get_quote("RELIANCE")
                    assert res["price"] == 105.0
                    assert res["previous_close"] == 100.0

@pytest.mark.asyncio
async def test_get_quote_indian_api_fallback(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            with patch("yfinance.Ticker", side_effect=Exception("yf error")):
                with patch("app.services.indian_stock_api.IndianStockAPI.fetch_quote") as mock_api:
                    mock_api.return_value = {"price": 300}
                    res = await MarketDataService.get_quote("RELIANCE")
                    assert res["price"] == 300
                    assert res["source"] == "IndianStockAPI"

@pytest.mark.asyncio
async def test_get_quote_all_fail(mock_redis):
    with patch("app.services.upstox_service.UpstoxService.get_cached_quote", return_value=None):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            with patch("yfinance.Ticker", side_effect=Exception("yf error")):
                with patch("app.services.indian_stock_api.IndianStockAPI.fetch_quote", side_effect=Exception("api error")):
                    with pytest.raises(ValueError):
                        await MarketDataService.get_quote("RELIANCE")

@pytest.mark.asyncio
async def test_get_history_redis_cache(mock_redis):
    with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
        mock_redis.get.return_value = json.dumps({"bars": [{"time": "2023-01-01", "close": 100}], "source": "redis"})
        res = await MarketDataService.get_history("RELIANCE", "1d", "5d")
        assert len(res) == 1
        assert res[0]["close"] == 100

@pytest.mark.asyncio
async def test_get_history_redis_cache_error(mock_redis):
    with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
        mock_redis.get.return_value = json.dumps({"error": True})
        res = await MarketDataService.get_history("RELIANCE", "1d", "5d")
        assert res == []

@pytest.mark.asyncio
async def test_get_history_yfinance_success(mock_redis):
    with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
        with patch("yfinance.download") as mock_yf:
            mock_yf.return_value = pd.DataFrame({
                "Date": [pd.Timestamp("2023-01-01")],
                "Open": [100.0],
                "High": [110.0],
                "Low": [90.0],
                "Close": [105.0],
                "Volume": [1000]
            })
            res = await MarketDataService.get_history("RELIANCE", "1d", "5d")
            assert len(res) == 1
            assert res[0]["close"] == 105.0

@pytest.mark.asyncio
async def test_get_history_yfinance_fail(mock_redis):
    with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
        with patch("yfinance.download", side_effect=Exception("error")):
            res = await MarketDataService.get_history("RELIANCE", "1d", "5d")
            assert res is None

@pytest.mark.asyncio
async def test_get_intraday_candles_success():
    with patch.object(MarketDataService, "get_history", return_value=[{"close": 100}]):
        res = await MarketDataService.get_intraday_candles("RELIANCE", "1m")
        assert len(res) == 1
        assert res[0]["close"] == 100

@pytest.mark.asyncio
async def test_get_intraday_candles_fallback():
    with patch.object(MarketDataService, "get_history", side_effect=Exception("error")):
        with patch.object(MarketDataService, "get_quote", return_value={"price": 100, "volume": 10}):
            res = await MarketDataService.get_intraday_candles("RELIANCE", "1m")
            assert len(res) == 1
            assert res[0]["close"] == 100

@pytest.mark.asyncio
async def test_get_movers():
    with patch.object(MarketDataService, "get_quote", return_value={"symbol": "RELIANCE.NS", "price": 100, "change_pct": 5.0, "volume": 1000}):
        res = await MarketDataService.get_movers(n=2, mover_type="gainers")
        assert len(res) == 2

@pytest.mark.asyncio
async def test_get_indices():
    with patch.object(MarketDataService, "get_quote", return_value={"price": 100, "change": 1, "change_pct": 1.0}):
        res = await MarketDataService.get_indices()
        assert len(res) == 3

@pytest.mark.asyncio
async def test_get_ticker_info():
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.info = {"trailingPE": 20, "marketCap": 1000, "shortName": "Reliance"}
        mock_ticker_cls.return_value = mock_ticker
        res = await MarketDataService.get_ticker_info("RELIANCE")
        assert res["trailingPE"] == 20

@pytest.mark.asyncio
async def test_get_ticker_history_df():
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [1, 2]})
        mock_ticker_cls.return_value = mock_ticker
        res = await MarketDataService.get_ticker_history_df("RELIANCE", "1d", "1d")
        assert not res.empty

@pytest.mark.asyncio
async def test_download_raw():
    with patch("yfinance.download") as mock_yf:
        mock_yf.return_value = pd.DataFrame({"Close": [1, 2]})
        res = await MarketDataService.download_raw("RELIANCE", "2023-01-01", "2023-01-02", "1d")
        assert not res.empty

@pytest.mark.asyncio
async def test_get_live_quote_success():
    with patch.object(MarketDataService, "get_quote", return_value={"price": 100}):
        res = await MarketDataService.get_live_quote("RELIANCE")
        assert res["price"] == 100

@pytest.mark.asyncio
async def test_get_live_quote_cache_fallback(mock_redis):
    with patch.object(MarketDataService, "get_quote", side_effect=Exception("error")):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            mock_redis.get.return_value = json.dumps({"price": 200})
            res = await MarketDataService.get_live_quote("RELIANCE")
            assert res["price"] == 200

@pytest.mark.asyncio
async def test_get_live_quote_fail(mock_redis):
    with patch.object(MarketDataService, "get_quote", side_effect=Exception("error")):
        with patch("app.database.redis_client.get_redis_client", return_value=mock_redis):
            mock_redis.get.return_value = None
            from fastapi import HTTPException
            with pytest.raises(HTTPException):
                await MarketDataService.get_live_quote("RELIANCE")

def test_get_ohlcv_sync():
    with patch("yfinance.Ticker") as mock_t:
        mock_t.return_value.history.return_value = pd.DataFrame({
            "Date": [pd.Timestamp("2023-01-01")],
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1000]
        })
        res = MarketDataService._fetch_ohlcv_sync("RELIANCE", "1d", "1d")
        assert len(res) == 1
        assert res[0]["close"] == 105.0

@pytest.mark.asyncio
async def test_get_ohlcv():
    with patch.object(MarketDataService, "_fetch_ohlcv_sync", return_value=[{"close": 100}]):
        res = await MarketDataService.get_ohlcv("RELIANCE", "1d", "1d")
        assert len(res) == 1

@pytest.mark.asyncio
async def test_get_ohlcv_fallback():
    with patch.object(MarketDataService, "_fetch_ohlcv_sync", side_effect=Exception("error")):
        with patch.object(MarketDataService, "get_history", return_value=[{"time": "2023-01-01T00:00:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]):
            res = await MarketDataService.get_ohlcv("RELIANCE", "1d", "1d")
            assert len(res) == 1

@pytest.mark.asyncio
async def test_get_nifty50_movers():
    with patch.object(MarketDataService, "_fetch_movers_sync", return_value={"gainers": [], "losers": []}):
        res = await MarketDataService.get_nifty50_movers()
        assert "gainers" in res

def test_fetch_movers_sync():
    with patch("yfinance.download") as mock_yf:
        df_data = {
            ("RELIANCE.NS", "Close"): [100.0, 105.0],
            ("TCS.NS", "Close"): [200.0, 190.0]
        }
        mock_df = pd.DataFrame(df_data)
        mock_df.columns = pd.MultiIndex.from_tuples([("RELIANCE.NS", "Close"), ("TCS.NS", "Close")])
        mock_yf.return_value = mock_df
        
        res = MarketDataService._fetch_movers_sync()
        assert len(res["gainers"]) > 0 or len(res["losers"]) > 0

def teardown_module(module):
    from tests.conftest import mock_get_quote, mock_get_history, mock_get_ticker_history_df, mock_get_ticker_info
    from app.services import market_data_service
    market_data_service.MarketDataService.get_quote = mock_get_quote
    market_data_service.MarketDataService.get_history = mock_get_history
    market_data_service.MarketDataService.get_ticker_history_df = mock_get_ticker_history_df
    market_data_service.MarketDataService.get_ticker_info = mock_get_ticker_info

