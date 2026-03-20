"""NSE India adapter with fallback behavior for unsupported intervals."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar


class NSESource(MarketDataSource):
    """Fetch NSE historical data and normalize to OHLCV.

    Endpoint coverage is used for daily bars. Intraday is intentionally rejected
    in this adapter to avoid silently wrong sampling.
    """

    name = "nse"
    _base_url = "https://www.nseindia.com/api/historical/cm/equity"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval != "1d":
            raise DataSourceError("NSE adapter currently supports daily interval only")

        params = {
            "symbol": symbol.replace(".NS", ""),
            "from": start.strftime("%d-%m-%Y"),
            "to": end.strftime("%d-%m-%Y"),
            "series": "[\"EQ\"]",
        }
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0",
            "referer": "https://www.nseindia.com/",
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            await client.get("https://www.nseindia.com", headers=headers)
            response = await client.get(self._base_url, params=params, headers=headers)
            if response.status_code >= 400:
                raise DataSourceError(f"NSE request failed for {symbol}: {response.status_code}")
            payload = response.json()

        rows = payload.get("data", [])
        bars: list[OHLCVBar] = []
        for row in rows:
            date_str = row.get("CH_TIMESTAMP")
            if not date_str:
                continue
            ts = datetime.strptime(date_str, "%d-%b-%Y").replace(tzinfo=UTC)
            bars.append(
                OHLCVBar(
                    time=ts,
                    open=float(row["CH_OPENING_PRICE"]),
                    high=float(row["CH_TRADE_HIGH_PRICE"]),
                    low=float(row["CH_TRADE_LOW_PRICE"]),
                    close=float(row["CH_CLOSING_PRICE"]),
                    volume=float(row.get("CH_TOT_TRADED_QTY", 0.0) or 0.0),
                    adjusted_close=None,
                    interval="1d",
                )
            )

        bars.sort(key=lambda x: x.time)
        return bars
