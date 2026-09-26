import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from uuid import uuid4

import pandas as pd
import pytest

import app.services.market_data_service as mds_module
from app.services.market_data_service import MarketDataService, TokenBucket, safe_float

# conftest.py overrides these 4 methods globally at collection time and
# saves the real implementations as _original_*. Restore them here directly
# rather than importlib.reload()-ing this module: re-executing its
# top-level code a second time (after the rest of the suite's
# native-extension state is already initialized) segfaults the interpreter.
MarketDataService.get_quote = mds_module.MarketDataService._original_get_quote
MarketDataService.get_history = mds_module.MarketDataService._original_get_history
MarketDataService.get_ticker_history_df = (
    mds_module.MarketDataService._original_get_ticker_history_df
)
MarketDataService.get_ticker_info = mds_module.MarketDataService._original_get_ticker_info


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
    # Canonical form is bare (no provider suffix), matching
    # Instrument.canonical_symbol in the canonical DB; a provider-suffixed
    # input is passed through unchanged rather than double-normalized.
    assert MarketDataService._normalize_symbol("RELIANCE") == "RELIANCE"
    assert MarketDataService._normalize_symbol("reliance") == "RELIANCE"
    assert MarketDataService._normalize_symbol("RELIANCE.NS") == "RELIANCE.NS"
    assert MarketDataService._normalize_symbol("USDINR=X") == "USDINR=X"
    assert MarketDataService._normalize_symbol("CL=F") == "CL=F"

@pytest.mark.asyncio
async def test_get_batch_quotes():
    with patch.object(MarketDataService, "get_quote", side_effect=[{"price": 100}, Exception("error")]):
        res = await MarketDataService.get_batch_quotes(["RELIANCE", "INVALID"])
        assert res["RELIANCE"] == {"price": 100}
        assert res["INVALID"] is None

def _mock_db_ctx(execute_results):
    """Patch app.database.connection.async_session_factory so that
    `async with async_session_factory() as db` yields a fake session whose
    db.execute() calls return execute_results in sequence, matching how
    get_quote/get_history call async_session_factory directly."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=execute_results)
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = False
    return patch(
        "app.database.connection.async_session_factory", return_value=mock_cm
    )


def _instrument_result(instrument_id):
    res = MagicMock()
    inst = MagicMock()
    inst.id = instrument_id
    res.scalars.return_value.first.return_value = inst
    return res


def _empty_result():
    res = MagicMock()
    res.scalars.return_value.first.return_value = None
    return res


@pytest.mark.asyncio
async def test_get_quote_db_success():
    inst_id = uuid4()
    quote = MagicMock()
    quote.price = 105.0
    quote.change = 5.0
    quote.change_pct = 5.0
    quote.volume = 1000
    quote.observed_at = datetime(2023, 1, 1, tzinfo=UTC)
    quote_res = MagicMock()
    quote_res.scalars.return_value.first.return_value = quote

    with _mock_db_ctx([_instrument_result(inst_id), quote_res]):
        res = await MarketDataService.get_quote("RELIANCE")
        assert res["price"] == 105.0
        assert res["source"] == "canonical_db"


@pytest.mark.asyncio
async def test_get_quote_instrument_not_found():
    with _mock_db_ctx([_empty_result()]):
        with pytest.raises(ValueError):
            await MarketDataService.get_quote("NOSUCHSYMBOL")


@pytest.mark.asyncio
async def test_get_quote_no_quote_data():
    inst_id = uuid4()
    with _mock_db_ctx([_instrument_result(inst_id), _empty_result()]):
        with pytest.raises(ValueError):
            await MarketDataService.get_quote("RELIANCE")


@pytest.mark.asyncio
async def test_get_history_db_success():
    inst_id = uuid4()
    bar = MagicMock()
    bar.timestamp = datetime(2023, 1, 1, tzinfo=UTC)
    bar.open = 100.0
    bar.high = 110.0
    bar.low = 90.0
    bar.close = 105.0
    bar.volume = 1000
    ohlcv_res = MagicMock()
    ohlcv_res.scalars.return_value.all.return_value = [bar]

    with _mock_db_ctx([_instrument_result(inst_id), ohlcv_res]):
        res = await MarketDataService.get_history("RELIANCE", "1d", "5d")
        assert len(res) == 1
        assert res[0]["close"] == 105.0
        assert res.source == "canonical_db"


@pytest.mark.asyncio
async def test_get_history_instrument_not_found():
    with _mock_db_ctx([_empty_result()]):
        res = await MarketDataService.get_history("NOSUCHSYMBOL", "1d", "5d")
        assert res == []
        assert res.source == "canonical_db"

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

def teardown_module(module):
    from app.services import market_data_service
    from tests.conftest import (
        mock_get_history,
        mock_get_quote,
        mock_get_ticker_history_df,
        mock_get_ticker_info,
    )
    market_data_service.MarketDataService.get_quote = mock_get_quote
    market_data_service.MarketDataService.get_history = mock_get_history
    market_data_service.MarketDataService.get_ticker_history_df = mock_get_ticker_history_df
    market_data_service.MarketDataService.get_ticker_info = mock_get_ticker_info

