"""Tests for app.services.ingestion.upstox_source.UpstoxSource.

HTTP is mocked at the _get() method boundary (this codebase has no
aiohttp-level mocking convention or dependency) so these tests verify
the real logic this file owns: instrument_key resolution via
InstrumentAlias, interval mapping, response parsing into Quote/OHLCVBar,
and error propagation - not aiohttp's own behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.base import DataUnavailableError, RateLimitExceededError
from app.services.ingestion.upstox_source import UpstoxAuthError, UpstoxSource


def _mock_db_session_returning(value):
    """Build a mock async_session_factory() context manager whose
    .execute(...).scalars().first() returns `value`."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = value
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_factory


@pytest.mark.asyncio
async def test_resolve_instrument_key_found():
    from app.services.ingestion.upstox_source import _resolve_instrument_key

    with patch(
        "app.database.connection.async_session_factory",
        _mock_db_session_returning("NSE_EQ|INE002A01018"),
    ):
        key = await _resolve_instrument_key("RELIANCE")
    assert key == "NSE_EQ|INE002A01018"


@pytest.mark.asyncio
async def test_resolve_instrument_key_missing_raises_data_unavailable():
    """No fabricated fallback: an unmapped symbol must fail honestly,
    not silently guess an instrument_key."""
    from app.services.ingestion.upstox_source import _resolve_instrument_key

    with patch("app.database.connection.async_session_factory", _mock_db_session_returning(None)):
        with pytest.raises(DataUnavailableError):
            await _resolve_instrument_key("NOT_MAPPED_YET")


def test_headers_raises_auth_error_when_token_missing():
    provider = UpstoxSource(token="")
    with pytest.raises(UpstoxAuthError):
        provider._headers()


def test_headers_includes_bearer_token():
    provider = UpstoxSource(token="abc123")
    headers = provider._headers()
    assert headers["Authorization"] == "Bearer abc123"


@pytest.mark.asyncio
async def test_get_quote_parses_ohlc_response():
    provider = UpstoxSource(token="fake-token")
    fake_response = {
        "status": "success",
        "data": {
            "NSE_EQ|INE002A01018": {
                "live_ohlc": {"open": 100, "high": 105, "low": 99, "close": 104, "volume": 123456},
                "prev_ohlc": {"open": 98, "high": 102, "low": 97, "close": 100},
            }
        },
    }
    with (
        patch(
            "app.services.ingestion.upstox_source._resolve_instrument_key",
            AsyncMock(return_value="NSE_EQ|INE002A01018"),
        ),
        patch.object(provider, "_get", AsyncMock(return_value=fake_response)),
    ):
        quote = await provider.get_quote("RELIANCE")

    assert quote.symbol == "RELIANCE"
    assert quote.price == 104.0
    assert quote.change == 4.0
    assert quote.change_pct == pytest.approx(4.0, rel=1e-3)
    assert quote.volume == 123456.0


@pytest.mark.asyncio
async def test_get_quote_propagates_unmapped_symbol():
    provider = UpstoxSource(token="fake-token")
    with patch(
        "app.services.ingestion.upstox_source._resolve_instrument_key",
        AsyncMock(side_effect=DataUnavailableError("no mapping")),
    ):
        with pytest.raises(DataUnavailableError):
            await provider.get_quote("UNMAPPED")


@pytest.mark.asyncio
async def test_get_ohlcv_rejects_unsupported_interval():
    provider = UpstoxSource(token="fake-token")
    with pytest.raises(DataUnavailableError):
        # "1w" and "1mo" are supported since the v3 historical-candle API was
        # adopted (see _INTERVAL_MAP), so use an interval Upstox has no mapping for.
        await provider.get_ohlcv("RELIANCE", "4h", datetime(2024, 1, 1), datetime(2024, 1, 31))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_ohlcv_parses_and_sorts_candles():
    provider = UpstoxSource(token="fake-token")
    fake_response = {
        "status": "success",
        "data": {
            "candles": [
                ["2024-01-02T00:00:00+05:30", 101, 106, 100, 105, 5000, 0],
                ["2024-01-01T00:00:00+05:30", 100, 104, 99, 103, 4000, 0],
            ]
        },
    }
    with (
        patch(
            "app.services.ingestion.upstox_source._resolve_instrument_key",
            AsyncMock(return_value="NSE_EQ|INE002A01018"),
        ),
        patch.object(provider, "_get", AsyncMock(return_value=fake_response)),
    ):
        bars = await provider.get_ohlcv(
            "RELIANCE", "1d", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 2, tzinfo=UTC)
        )

    assert len(bars) == 2
    # Sorted chronologically even though the API returned newest-first.
    assert bars[0].time < bars[1].time
    assert bars[0].close == 103.0
    assert bars[1].close == 105.0


@pytest.mark.asyncio
async def test_health_reports_down_without_making_a_call_when_token_missing():
    provider = UpstoxSource(token="")
    with patch.object(provider, "_get", AsyncMock()) as mock_get:
        result = await provider.health()
    mock_get.assert_not_called()
    assert result["status"] == "down"
    assert "UPSTOX_ANALYTICS_TOKEN" in result["error"]


@pytest.mark.asyncio
async def test_get_raises_auth_error_on_401():
    """Verifies the actual status-code branching in _get() itself, not
    just callers' handling of a pre-mocked exception."""
    provider = UpstoxSource(token="bad-token")

    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(UpstoxAuthError):
            await provider._get("/v3/market-quote/ohlc")


@pytest.mark.asyncio
async def test_get_raises_rate_limit_error_on_429():
    provider = UpstoxSource(token="fake-token")

    mock_response = MagicMock()
    mock_response.status = 429
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(RateLimitExceededError):
            await provider._get("/v3/market-quote/ohlc")
