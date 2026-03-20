"""FRED macro series adapter converted to OHLCV-compatible records."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

settings = get_settings()


class FREDSource(MarketDataSource):
    """Fetch FRED observations and normalize into synthetic OHLCV bars.

    FRED provides one value per date. We map this to open=high=low=close.
    """

    name = "fred"
    _base_url = "https://api.stlouisfed.org/fred/series/observations"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval != "1d":
            raise DataSourceError("FRED source is daily-only")

        params = {
            "series_id": symbol,
            "api_key": settings.FRED_API_KEY,
            "file_type": "json",
            "observation_start": start.date().isoformat(),
            "observation_end": end.date().isoformat(),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._base_url, params=params)
            if response.status_code >= 400:
                raise DataSourceError(f"FRED request failed for {symbol}: {response.status_code}")
            payload = response.json()

        rows = payload.get("observations", [])
        bars: list[OHLCVBar] = []
        for row in rows:
            value_str = row.get("value", ".")
            if value_str in {".", "", None}:
                continue
            value = float(value_str)
            ts = datetime.fromisoformat(row["date"] + "T00:00:00+00:00").astimezone(UTC)
            bars.append(
                OHLCVBar(
                    time=ts,
                    open=value,
                    high=value,
                    low=value,
                    close=value,
                    volume=0.0,
                    adjusted_close=None,
                    interval="1d",
                )
            )

        return bars
