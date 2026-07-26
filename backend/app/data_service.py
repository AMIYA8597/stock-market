import logging
import os
from datetime import datetime
from functools import lru_cache

import requests
import yfinance as yf

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def fetch_alpha_vantage(ticker: str, interval: str = "5min"):
    """Fetch real‑time intraday data from Alpha Vantage.
    Returns a list of dicts with keys: time, open, high, low, close, volume.
    """
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": ticker,
        "interval": interval,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": "compact",
        "datatype": "json",
    }
    resp = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    key = f"Time Series ({interval})"
    if key not in data:
        raise ValueError(f"Alpha Vantage error: {data.get('Note') or data.get('Error Message')}")
    series = []
    for ts, vals in data[key].items():
        series.append(
            {
                "time": datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"),
                "open": float(vals["1. open"]),
                "high": float(vals["2. high"]),
                "low": float(vals["3. low"]),
                "close": float(vals["4. close"]),
                "volume": int(vals["5. volume"]),
            }
        )
    # Sort newest last
    series.sort(key=lambda x: x["time"])
    return series


@lru_cache(maxsize=128)
def fetch_yfinance(ticker: str, period: str = "1d", interval: str = "5m"):
    """Fetch historical data using yfinance.
    Returns a list of dicts similar to fetch_alpha_vantage.
    """
    ticker_obj = yf.Ticker(ticker)
    hist = ticker_obj.history(period=period, interval=interval)
    series = []
    for idx, row in hist.iterrows():
        series.append(
            {
                "time": idx.to_pydatetime(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
        )
    return series


def get_latest_price(ticker: str):
    """Return the most recent OHLC record.
    Tries Alpha Vantage first, falls back to yfinance.
    """
    try:
        data = fetch_alpha_vantage(ticker)
    except Exception as exc:
        logger.warning(f"Alpha Vantage fetch failed for {ticker}, falling back to yfinance: {exc}")
        data = fetch_yfinance(ticker, period="1d", interval="5m")
    return data[-1] if data else None


def get_historical(ticker: str, days: int = 30):
    """Return OHLC data for the past *days*.
    Uses yfinance for longer history.
    """
    period = f"{days}d"
    return fetch_yfinance(ticker, period=period, interval="1d")
