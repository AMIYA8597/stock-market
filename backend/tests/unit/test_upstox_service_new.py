from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.upstox_service import (
    KEY_TO_SYMBOL,
    SYMBOL_TO_KEY,
    UPSTOX_TICK_CACHE,
    UpstoxService,
)


@pytest.fixture(autouse=True)
def reset_service_state():
    UpstoxService.ACCESS_TOKEN = None
    UpstoxService.STREAMER = None
    UpstoxService.CONNECTION_STATUS = "disconnected"
    UpstoxService.USER_PROFILE = None
    UpstoxService.LOOP = None
    UPSTOX_TICK_CACHE.clear()
    SYMBOL_TO_KEY.clear()
    KEY_TO_SYMBOL.clear()
    yield

def test_get_token_cache_path():
    path = UpstoxService.get_token_cache_path()
    assert isinstance(path, Path)
    assert path.name == "upstox_token.txt"

def test_log_audit(tmp_path):
    with patch("app.services.upstox_service.Path.resolve") as mock_resolve:
        mock_backend_root = tmp_path / "backend"
        mock_backend_root.mkdir()
        mock_resolve.return_value.parent.parent.parent = mock_backend_root

        UpstoxService.log_audit("Test message")

        logs_dir = mock_backend_root / "logs"
        audit_file = logs_dir / "trading_audit.log"
        assert audit_file.exists()
        content = audit_file.read_text(encoding="utf-8")
        assert "Test message" in content

def test_get_cached_quote():
    UPSTOX_TICK_CACHE["RELIANCE"] = {"price": 100}
    assert UpstoxService.get_cached_quote("RELIANCE") == {"price": 100}
    assert UpstoxService.get_cached_quote("RELIANCE.NS") == {"price": 100}
    assert UpstoxService.get_cached_quote("UNKNOWN") is None

@patch("app.core.config.get_settings")
def test_get_login_url(mock_settings):
    mock_settings.return_value.UPSTOX_API_KEY = "test_key"
    mock_settings.return_value.UPSTOX_REDIRECT_URI = "http://localhost/callback"
    url = UpstoxService.get_login_url()
    assert "client_id=test_key" in url
    assert "redirect_uri=http://localhost/callback" in url

@patch("app.core.config.get_settings")
def test_get_login_url_missing_key(mock_settings):
    mock_settings.return_value.UPSTOX_API_KEY = None
    with pytest.raises(ValueError):
        UpstoxService.get_login_url()

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.post")
@patch("app.core.config.get_settings")
@patch("app.services.upstox_service.UpstoxService.fetch_profile")
@patch("app.services.upstox_service.UpstoxService.start_websocket_feed")
async def test_exchange_code_for_token(mock_start_ws, mock_fetch_profile, mock_settings, mock_post, tmp_path):
    mock_settings.return_value.UPSTOX_API_KEY = "key"
    mock_settings.return_value.UPSTOX_API_SECRET = "secret"
    mock_settings.return_value.UPSTOX_REDIRECT_URI = "uri"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "test_token"}
    mock_post.return_value = mock_response

    mock_fetch_profile.return_value = {"user_name": "Test User"}

    with patch("app.services.upstox_service.UpstoxService.get_token_cache_path", return_value=tmp_path / "token.txt"):
        res = await UpstoxService.exchange_code_for_token("test_code")

        assert res == {"access_token": "test_token"}
        assert UpstoxService.ACCESS_TOKEN == "test_token"
        assert UpstoxService.USER_PROFILE == {"user_name": "Test User"}
        mock_start_ws.assert_called_once()
        assert (tmp_path / "token.txt").read_text() == "test_token"

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.post")
@patch("app.core.config.get_settings")
async def test_exchange_code_for_token_failure(mock_settings, mock_post):
    mock_settings.return_value.UPSTOX_API_KEY = "key"
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Error"
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="Token exchange failed"):
        await UpstoxService.exchange_code_for_token("test_code")

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.post")
@patch("app.core.config.get_settings")
async def test_exchange_code_for_token_missing_token(mock_settings, mock_post):
    mock_settings.return_value.UPSTOX_API_KEY = "key"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="Access token missing"):
        await UpstoxService.exchange_code_for_token("test_code")

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.get")
async def test_fetch_profile(mock_get):
    UpstoxService.ACCESS_TOKEN = "token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"user_name": "Test"}}
    mock_get.return_value = mock_response

    profile = await UpstoxService.fetch_profile()
    assert profile == {"user_name": "Test"}

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.get")
async def test_fetch_profile_failure(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    profile = await UpstoxService.fetch_profile()
    assert profile == {}

@pytest.mark.asyncio
@patch("app.services.upstox_service.UpstoxService.fetch_profile")
@patch("app.services.upstox_service.UpstoxService.start_websocket_feed")
async def test_init_service_with_valid_token(mock_start_ws, mock_fetch_profile, tmp_path):
    token_file = tmp_path / "upstox_token.txt"
    token_file.write_text("valid_token")
    mock_fetch_profile.return_value = {"user_name": "Test"}

    with patch("app.services.upstox_service.UpstoxService.get_token_cache_path", return_value=token_file):
        await UpstoxService.init_service()
        assert UpstoxService.ACCESS_TOKEN == "valid_token"
        assert UpstoxService.USER_PROFILE == {"user_name": "Test"}
        mock_start_ws.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.upstox_service.UpstoxService.fetch_profile")
async def test_init_service_with_invalid_token(mock_fetch_profile, tmp_path):
    token_file = tmp_path / "upstox_token.txt"
    token_file.write_text("invalid_token")
    mock_fetch_profile.return_value = {}

    with patch("app.services.upstox_service.UpstoxService.get_token_cache_path", return_value=token_file):
        await UpstoxService.init_service()
        assert UpstoxService.ACCESS_TOKEN is None

@pytest.mark.asyncio
async def test_resolve_symbol_cache_and_overrides():
    SYMBOL_TO_KEY["RELIANCE"] = "key1"
    assert await UpstoxService.resolve_symbol("RELIANCE") == "key1"

    assert await UpstoxService.resolve_symbol("NIFTY 50") == "NSE_INDEX|Nifty 50"
    assert SYMBOL_TO_KEY["NIFTY 50"] == "NSE_INDEX|Nifty 50"

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.get")
async def test_resolve_symbol_api_search_exact_match(mock_get):
    UpstoxService.ACCESS_TOKEN = "token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"trading_symbol": "TCS", "segment": "NSE_EQ", "instrument_key": "tcs_key"}
        ]
    }
    mock_get.return_value = mock_response

    key = await UpstoxService.resolve_symbol("TCS")
    assert key == "tcs_key"
    assert SYMBOL_TO_KEY["TCS"] == "tcs_key"

@pytest.mark.asyncio
@patch("app.services.upstox_service.httpx.AsyncClient.get")
async def test_resolve_symbol_api_search_partial_match(mock_get):
    UpstoxService.ACCESS_TOKEN = "token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"trading_symbol": "INFY-EQ", "segment": "NSE_EQ", "instrument_key": "infy_key"}
        ]
    }
    mock_get.return_value = mock_response

    key = await UpstoxService.resolve_symbol("INFY")
    assert key == "infy_key"

@pytest.mark.asyncio
async def test_start_websocket_feed_no_token():
    await UpstoxService.start_websocket_feed()
    assert UpstoxService.CONNECTION_STATUS == "disconnected"

@pytest.mark.asyncio
@patch("app.services.upstox_service.upstox_client")
@patch("app.services.upstox_service.UpstoxService.resolve_symbol")
async def test_start_websocket_feed_success(mock_resolve, mock_upstox_client):
    UpstoxService.ACCESS_TOKEN = "token"
    mock_resolve.side_effect = lambda sym: f"key_{sym}"

    mock_streamer = MagicMock()
    mock_upstox_client.MarketDataStreamerV3.return_value = mock_streamer

    await UpstoxService.start_websocket_feed()

    assert UpstoxService.CONNECTION_STATUS == "connecting"
    assert UpstoxService.STREAMER == mock_streamer
    mock_streamer.connect.assert_called_once()
    mock_streamer.on.assert_called()

@pytest.mark.asyncio
@patch("app.services.upstox_service.UpstoxService.resolve_symbol")
async def test_start_websocket_feed_no_symbols(mock_resolve):
    UpstoxService.ACCESS_TOKEN = "token"
    mock_resolve.return_value = None

    await UpstoxService.start_websocket_feed()
    assert UpstoxService.STREAMER is None

@pytest.mark.asyncio
async def test_stop_websocket_feed():
    mock_streamer = MagicMock()
    UpstoxService.STREAMER = mock_streamer
    await UpstoxService.stop_websocket_feed()
    mock_streamer.disconnect.assert_called_once()
    assert UpstoxService.STREAMER is None
    assert UpstoxService.CONNECTION_STATUS == "disconnected"

def test_streamer_callbacks():
    UpstoxService.on_open()
    assert UpstoxService.CONNECTION_STATUS == "connected"

    UpstoxService.on_close(200, "Closed")
    assert UpstoxService.CONNECTION_STATUS == "disconnected"

    UpstoxService.on_error("error")
    assert UpstoxService.CONNECTION_STATUS == "error"

    UpstoxService.on_reconnecting("reconnect")
    assert UpstoxService.CONNECTION_STATUS == "reconnecting"

@patch("app.services.upstox_service.asyncio.run_coroutine_threadsafe")
def test_on_message(mock_run_coroutine):
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = True
    UpstoxService.LOOP = mock_loop
    KEY_TO_SYMBOL["key1"] = "RELIANCE"

    msg = {
        "feeds": {
            "key1": {
                "ltpc": {"ltp": 105.0, "cp": 100.0}
            }
        }
    }

    UpstoxService.on_message(msg)

    assert "RELIANCE" in UPSTOX_TICK_CACHE
    tick = UPSTOX_TICK_CACHE["RELIANCE"]
    assert tick["price"] == 105.0
    assert tick["change"] == 5.0
    assert tick["change_pct"] == 5.0
    mock_run_coroutine.assert_called_once()

@patch("app.services.upstox_service.asyncio.run_coroutine_threadsafe")
def test_on_message_ff(mock_run_coroutine):
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = True
    UpstoxService.LOOP = mock_loop
    KEY_TO_SYMBOL["key2"] = "TCS"

    msg = {
        "feeds": {
            "key2": {
                "ff": {
                    "marketFF": {
                        "ltpc": {"ltp": 200.0, "cp": 190.0},
                        "marketOHLC": {"ohlc": [{"interval": "1d", "open": 195.0, "high": 205.0, "low": 190.0, "close": 190.0, "volume": 1000}]}
                    }
                }
            }
        }
    }

    UpstoxService.on_message(msg)

    assert "TCS" in UPSTOX_TICK_CACHE
    tick = UPSTOX_TICK_CACHE["TCS"]
    assert tick["price"] == 200.0
    assert tick["open"] == 195.0
    mock_run_coroutine.assert_called_once()

@pytest.mark.asyncio
@patch("app.database.redis_client.get_redis_client")
@patch("app.services.upstox_service.UpstoxService.enrich_tick_with_indicators")
@patch("app.services.paper_trading.PaperTradingService.check_and_execute_limit_orders")
@patch("app.database.connection.async_session_factory")
async def test_publish_tick_to_redis(mock_session_factory, mock_check_orders, mock_enrich, mock_get_redis):
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    mock_enrich.return_value = {"symbol": "RELIANCE", "price": 100, "enriched": True}

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    tick = {"symbol": "RELIANCE", "price": 100}
    await UpstoxService.publish_tick_to_redis(tick)

    mock_enrich.assert_called_once_with(tick)
    mock_redis.publish.assert_called_once()
    mock_check_orders.assert_called_once_with(mock_session, "RELIANCE", Decimal("100"))

@pytest.mark.asyncio
@patch("app.services.market_data_service.MarketDataService.get_history")
@patch("research.feature_engineering.pipeline.FeaturePipeline.run")
async def test_enrich_tick_with_indicators(mock_pipeline_run, mock_get_history):
    mock_get_history.return_value = [
        {"open": 90, "high": 110, "low": 80, "close": 100, "volume": 1000}
    ] * 10

    def fake_pipeline_run(df):
        return df
    mock_pipeline_run.side_effect = fake_pipeline_run

    tick = {"symbol": "RELIANCE", "price": 105.0}

    enriched = await UpstoxService.enrich_tick_with_indicators(tick)

    assert "ema9" in enriched
    assert "rsi" in enriched
    assert mock_get_history.called

@pytest.mark.asyncio
@patch("app.services.market_data_service.MarketDataService.get_history")
async def test_enrich_tick_with_indicators_no_history(mock_get_history):
    mock_get_history.return_value = []

    tick = {"symbol": "RELIANCE", "price": 105.0}

    enriched = await UpstoxService.enrich_tick_with_indicators(tick)

    assert enriched["ema9"] is None


def test_log_audit_exception():
    with patch('app.services.upstox_service.Path.resolve', side_effect=Exception('Test Error')):
        UpstoxService.log_audit('msg')

@pytest.mark.asyncio
async def test_exchange_code_for_token_cache_error(tmp_path):
    with patch('app.core.config.get_settings'),          patch('app.services.upstox_service.httpx.AsyncClient.post') as mock_post,          patch('app.services.upstox_service.UpstoxService.fetch_profile', return_value={}),          patch('app.services.upstox_service.UpstoxService.start_websocket_feed'),          patch('app.services.upstox_service.UpstoxService.get_token_cache_path', side_effect=Exception('Cache Error')):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test'}
        mock_post.return_value = mock_response
        await UpstoxService.exchange_code_for_token('code')

@pytest.mark.asyncio
async def test_init_service_exception(tmp_path):
    with patch('app.services.upstox_service.UpstoxService.get_token_cache_path') as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.side_effect = Exception('Read Error')
        await UpstoxService.init_service()

@pytest.mark.asyncio
async def test_resolve_symbol_banknifty():
    assert await UpstoxService.resolve_symbol('NIFTY BANK') == 'NSE_INDEX|Nifty Bank'

@pytest.mark.asyncio
async def test_resolve_symbol_no_token():
    UpstoxService.ACCESS_TOKEN = None
    assert await UpstoxService.resolve_symbol('UNKNOWN') is None

@pytest.mark.asyncio
async def test_resolve_symbol_api_error():
    UpstoxService.ACCESS_TOKEN = 'token'
    with patch('app.services.upstox_service.httpx.AsyncClient.get', side_effect=Exception('API Error')):
        assert await UpstoxService.resolve_symbol('UNKNOWN') is None

@pytest.mark.asyncio
async def test_start_websocket_feed_error():
    UpstoxService.ACCESS_TOKEN = 'token'
    with patch('app.services.upstox_service.UpstoxService.resolve_symbol', return_value='key'),          patch('app.services.upstox_service.upstox_client.Configuration', side_effect=Exception('WS Error')):
        await UpstoxService.start_websocket_feed()

@pytest.mark.asyncio
async def test_stop_websocket_feed_error():
    mock_streamer = MagicMock()
    mock_streamer.disconnect.side_effect = Exception('Disconnect Error')
    UpstoxService.STREAMER = mock_streamer
    await UpstoxService.stop_websocket_feed()

def test_on_message_empty_or_unknown():
    UpstoxService.on_message({})
    UpstoxService.on_message({'feeds': {}})
    UpstoxService.on_message({'feeds': {'key_unknown': {}}})

def test_on_message_exception():
    with patch('app.services.upstox_service.KEY_TO_SYMBOL', side_effect=Exception('Unknown Error')):
        UpstoxService.on_message({'feeds': {'key1': {}}})

@pytest.mark.asyncio
async def test_publish_tick_to_redis_exception():
    with patch('app.database.redis_client.get_redis_client', side_effect=Exception('Redis Error')),          patch('app.services.upstox_service.UpstoxService.enrich_tick_with_indicators', return_value={}):
        await UpstoxService.publish_tick_to_redis({'symbol': 'RELIANCE', 'price': 100})

@pytest.mark.asyncio
async def test_publish_tick_to_redis_limit_order_exception():
    with patch('app.database.redis_client.get_redis_client'),          patch('app.services.upstox_service.UpstoxService.enrich_tick_with_indicators', return_value={}),          patch('app.database.connection.async_session_factory') as mock_factory:
        mock_factory.return_value.__aenter__.side_effect = Exception('Limit Order DB Error')
        await UpstoxService.publish_tick_to_redis({'symbol': 'RELIANCE', 'price': 100})

@pytest.mark.asyncio
async def test_enrich_tick_with_indicators_full(tmp_path):
    with patch('app.services.market_data_service.MarketDataService.get_history') as mock_hist,          patch('research.feature_engineering.pipeline.FeaturePipeline.run') as mock_pipeline:
        mock_hist.return_value = [
            {'open': 90, 'high': 110, 'low': 80, 'close': 100, 'volume': 1000}
        ] * 10
        def dummy_pipeline(df):
            return df
        mock_pipeline.side_effect = dummy_pipeline

        tick = {'symbol': 'RELIANCE', 'price': 105.0}
        res = await UpstoxService.enrich_tick_with_indicators(tick)
        assert res['ema9'] is not None

def test_import_error():
    import sys
    # simulate import error
    original = sys.modules.get('upstox_client')
    sys.modules['upstox_client'] = None
    import importlib

    import app.services.upstox_service
    importlib.reload(app.services.upstox_service)

    assert app.services.upstox_service.upstox_client is None

    if original:
        sys.modules['upstox_client'] = original
    else:
        del sys.modules['upstox_client']
    importlib.reload(app.services.upstox_service)
