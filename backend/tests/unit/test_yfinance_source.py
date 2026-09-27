"""Tests for app.services.ingestion.yfinance_source.

Regression coverage for a real bug: _to_yfinance_symbol (formerly an
inline ternary guarded by `not symbol.endswith("")`, which is always
False for any string) used to be dead code, so a bare canonical NSE
symbol like "RELIANCE" was sent to Yahoo Finance unchanged instead of
as "RELIANCE.NS" - which does not resolve on Yahoo Finance.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.ingestion.yfinance_source import YFinanceProvider, _to_yfinance_symbol


def test_to_yfinance_symbol_appends_ns_for_bare_equity_symbol():
    assert _to_yfinance_symbol("RELIANCE") == "RELIANCE.NS"
    assert _to_yfinance_symbol("TCS") == "TCS.NS"


def test_to_yfinance_symbol_passes_through_already_suffixed_symbols():
    assert _to_yfinance_symbol("RELIANCE.NS") == "RELIANCE.NS"
    assert _to_yfinance_symbol("RELIANCE.BO") == "RELIANCE.BO"


def test_to_yfinance_symbol_passes_through_indices_and_fx():
    assert _to_yfinance_symbol("^NSEI") == "^NSEI"
    assert _to_yfinance_symbol("USDINR=X") == "USDINR=X"


@pytest.mark.asyncio
async def test_get_quote_calls_yfinance_with_ns_suffixed_symbol():
    """Regression test: get_quote must actually request the .NS-suffixed
    ticker from yfinance for a bare canonical NSE symbol, not the raw
    canonical symbol - the bug this fixes silently requested the wrong
    (unsuffixed) ticker every time."""
    provider = YFinanceProvider()

    mock_ticker = MagicMock()
    mock_ticker.info = {"currentPrice": 100.0, "previousClose": 95.0, "regularMarketVolume": 1000}

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value = mock_ticker
        quote = await provider.get_quote("RELIANCE")

    mock_ticker_cls.assert_called_once_with("RELIANCE.NS")
    assert quote.price == 100.0


@pytest.mark.asyncio
async def test_get_ohlcv_calls_yfinance_with_ns_suffixed_symbol():
    import pandas as pd

    provider = YFinanceProvider()
    empty_df = pd.DataFrame()

    with patch("yfinance.download") as mock_download:
        mock_download.return_value = empty_df
        await provider.get_ohlcv(
            "RELIANCE", "1d", datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 31, tzinfo=UTC)
        )

    called_symbol = mock_download.call_args.args[0] if mock_download.call_args.args else mock_download.call_args.kwargs.get("tickers")
    assert called_symbol == "RELIANCE.NS"
