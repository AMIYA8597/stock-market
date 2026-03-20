"""CoinGecko OHLC adapter for crypto assets."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

settings = get_settings()


class CoinGeckoSource(MarketDataSource):
    """Fetch OHLCV data from CoinGecko market chart range endpoint."""

    name = "coingecko"
    _base_url = "https://api.coingecko.com/api/v3"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval not in {"1h", "1d"}:
            raise DataSourceError("CoinGecko supports only 1h and 1d in this adapter")

        coin_id = symbol.lower().replace("-usd", "").replace("usd", "")
        params = {
            "vs_currency": "usd",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
        }
        headers = {"accept": "application/json"}
        if settings.COINGECKO_API_KEY:
            headers["x-cg-pro-api-key"] = settings.COINGECKO_API_KEY

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self._base_url}/coins/{coin_id}/market_chart/range", params=params, headers=headers)
            if response.status_code >= 400:
                raise DataSourceError(f"CoinGecko request failed for {symbol}: {response.status_code}")
            payload = response.json()

        prices = payload.get("prices", [])
        volumes = payload.get("total_volumes", [])
        if not prices:
            return []

        volume_map = {int(ts): float(vol) for ts, vol in volumes}
        bars: list[OHLCVBar] = []

        prev_price = float(prices[0][1])
        for ts_ms, price in prices:
            ts = datetime.fromtimestamp(int(ts_ms) / 1000, tz=UTC)
            close = float(price)
            bars.append(
                OHLCVBar(
                    time=ts,
                    open=prev_price,
                    high=max(prev_price, close),
                    low=min(prev_price, close),
                    close=close,
                    volume=volume_map.get(int(ts_ms), 0.0),
                    adjusted_close=None,
                    interval=interval,
                )
            )
            prev_price = close

        return bars
