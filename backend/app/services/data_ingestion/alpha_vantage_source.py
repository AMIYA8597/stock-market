"""Alpha Vantage market data adapter.

Provides OHLCV data using the Alpha Vantage API. Requires an API key set in the
environment variable ``ALPHAVANTAGE_KEY``.
"""

from __future__ import annotations

import os
import asyncio
from datetime import datetime, UTC
from typing import Optional

import requests
import pandas as pd

from app.services.data_ingestion.base import (
    DataSourceError,
    Interval,
    MarketDataSource,
    OHLCVBar,
)


class AlphaVantageSource(MarketDataSource):
    """Fetch OHLCV data from Alpha Vantage.

    The free tier allows up to 5 requests per minute and 500 per day. The class
    respects this limitation by throttling calls.
    """

    name = "alpha_vantage"
    _semaphore = asyncio.Semaphore(4)  # limit concurrency
    _last_request_ts: float = 0.0

    @staticmethod
    def _get_api_key() -> str:
        key = os.getenv("ALPHAVANTAGE_KEY")
        if not key:
            raise DataSourceError("Alpha Vantage API key not configured (env ALPHAVANTAGE_KEY)")
        return key

    @classmethod
    async def _throttle(cls) -> None:
        """Ensure at most one request per 12 seconds (5 per minute)."""
        now = asyncio.get_event_loop().time()
        elapsed = now - cls._last_request_ts
        if elapsed < 12:
            await asyncio.sleep(12 - elapsed)
        cls._last_request_ts = asyncio.get_event_loop().time()

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        # Alpha Vantage uses its own interval strings – map the generic Interval
        # to the API format.
        av_interval_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "60m": "60min",
            "1h": "60min",
            "1d": "daily",
        }
        av_interval = av_interval_map.get(interval)
        if not av_interval:
            raise DataSourceError(f"Interval {interval} not supported by Alpha Vantage")

        api_key = self._get_api_key()
        base_url = "https://www.alphavantage.co/query"

        # Choose the correct function based on interval.
        function = "TIME_SERIES_INTRADAY" if "min" in av_interval else "TIME_SERIES_DAILY_ADJUSTED"
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": api_key,
            "outputsize": "full",
        }
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = av_interval
        params["datatype"] = "json"

        await self._throttle()
        async with self._semaphore:
            def _do_request() -> dict:
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
                return resp.json()

            data = await asyncio.to_thread(_do_request)

        if function == "TIME_SERIES_INTRADAY":
            key = f"Time Series ({av_interval})"
        else:
            key = "Time Series (Daily)"
        if key not in data:
            raise DataSourceError(f"Alpha Vantage response missing expected key {key} for {symbol}")

        raw = data[key]
        df = pd.DataFrame.from_dict(raw, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.apply(pd.to_numeric, errors="coerce")
        mask = (df.index >= start) & (df.index <= end)
        df = df.loc[mask]
        df = df.sort_index()

        bars: list[OHLCVBar] = []
        for ts, row in df.iterrows():
            open_ = row.get("1. open") if "1. open" in row else row.get("open")
            high_ = row.get("2. high") if "2. high" in row else row.get("high")
            low_ = row.get("3. low") if "3. low" in row else row.get("low")
            close_ = row.get("4. close") if "4. close" in row else row.get("close")
            volume_ = row.get("5. volume") if "5. volume" in row else row.get("volume")
            if any(v is None for v in (open_, high_, low_, close_, volume_)):
                continue
            bars.append(
                OHLCVBar(
                    time=ts.replace(tzinfo=UTC),
                    open=float(open_),
                    high=float(high_),
                    low=float(low_),
                    close=float(close_),
                    volume=float(volume_),
                    adjusted_close=None,
                    interval=interval,
                )
            )
        return bars
