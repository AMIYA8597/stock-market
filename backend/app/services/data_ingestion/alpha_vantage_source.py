"""Alpha Vantage OHLCV adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

settings = get_settings()


_INTERVAL_TO_FUNCTION: dict[Interval, str] = {
    "1m": "TIME_SERIES_INTRADAY",
    "5m": "TIME_SERIES_INTRADAY",
    "15m": "TIME_SERIES_INTRADAY",
    "1h": "TIME_SERIES_INTRADAY",
    "1d": "TIME_SERIES_DAILY_ADJUSTED",
}

_INTRADAY_INTERVAL_MAP: dict[Interval, str] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "60min",
    "1d": "",
}


class AlphaVantageSource(MarketDataSource):
    """Fetch OHLCV bars from Alpha Vantage with interval-aware parsing."""

    name = "alpha_vantage"
    _base_url = "https://www.alphavantage.co/query"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        function = _INTERVAL_TO_FUNCTION[interval]
        params: dict[str, str] = {
            "function": function,
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY,
            "outputsize": "full",
        }
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = _INTRADAY_INTERVAL_MAP[interval]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._base_url, params=params)
            if response.status_code >= 400:
                raise DataSourceError(f"Alpha Vantage failed for {symbol}: {response.status_code}")
            payload = response.json()

        if "Note" in payload:
            raise DataSourceError(f"Alpha Vantage rate limit for {symbol}")

        if function == "TIME_SERIES_DAILY_ADJUSTED":
            key = "Time Series (Daily)"
            series = payload.get(key, {})
        else:
            key = f"Time Series ({_INTRADAY_INTERVAL_MAP[interval]})"
            series = payload.get(key, {})

        bars: list[OHLCVBar] = []
        for ts_str, row in series.items():
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            else:
                ts = ts.astimezone(UTC)

            if ts < start or ts > end:
                continue

            bars.append(
                OHLCVBar(
                    time=ts,
                    open=float(row["1. open"]),
                    high=float(row["2. high"]),
                    low=float(row["3. low"]),
                    close=float(row["4. close"]),
                    volume=float(row.get("6. volume", row.get("5. volume", 0.0)) or 0.0),
                    adjusted_close=float(row["5. adjusted close"]) if "5. adjusted close" in row else None,
                    interval=interval,
                )
            )

        bars.sort(key=lambda x: x.time)
        return bars
