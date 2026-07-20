import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict

# Simple cache to avoid excessive API calls
_cache: Dict[str, pd.DataFrame] = {}
_CACHE_TTL_SECONDS = 30  # refresh every 30 seconds

def _is_cache_valid(symbol: str) -> bool:
    if symbol not in _cache:
        return False
    ts = _cache[symbol].attrs.get("fetched_at")
    if not ts:
        return False
    return (datetime.utcnow() - ts).total_seconds() < _CACHE_TTL_SECONDS

def fetch_ohlcv(symbol: str, interval: str = "1m", period: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data for a given symbol.

    Args:
        symbol: Stock ticker (e.g., "RELIANCE.NS").
        interval: Data interval ("1m", "5m", "15m", "1h", "1d").
        period: Historical period to retrieve (e.g., "1d", "5d", "1mo").

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume, and Datetime index.
    """
    cache_key = f"{symbol}_{interval}_{period}"
    if _is_cache_valid(cache_key):
        return _cache[cache_key]
    ticker = yf.Ticker(symbol)
    df = ticker.history(interval=interval, period=period)
    if df.empty:
        raise ValueError(f"No data returned for {symbol} with interval={interval}, period={period}")
    df = df.tz_convert(None)
    df.attrs["fetched_at"] = datetime.utcnow()
    _cache[cache_key] = df
    return df

def list_supported_symbols() -> List[str]:
    """Return a static list of a few popular Indian symbols for demo purposes."""
    return [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ITC.NS",
    ]
