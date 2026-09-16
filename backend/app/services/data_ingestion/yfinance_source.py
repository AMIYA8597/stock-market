"""Yahoo Finance market data provider."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.instrument import Instrument
from app.services.data_ingestion.base import (
    DataUnavailableError,
    Interval,
    MarketDataProvider,
    OHLCVBar,
    Quote,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)

_YF_INTERVAL_MAP: dict[Interval, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "60m",
    "1d": "1d",
}


class YFinanceProvider(MarketDataProvider):
    """Yahoo Finance provider implementation."""

    name = "yfinance"

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    @retry(
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError, DataUnavailableError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch(self, url: str) -> dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    raise RateLimitExceededError(f"{self.name} rate limit exceeded.")
                if response.status == 404:
                    raise DataUnavailableError(f"{self.name} returned 404 for url: {url}")
                if response.status >= 400:
                    raise DataUnavailableError(f"{self.name} returned {response.status}")
                return await response.json()

    async def get_quote(self, symbol: str) -> Quote:
        yf_symbol = (
            Instrument.normalize_symbol(symbol) + ".NS"
            if not symbol.endswith(".NS") and "^" not in symbol and "=" not in symbol
            else symbol
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}?interval=1m&range=1d"
        try:
            data = await self._fetch(url)
            result = data.get("chart", {}).get("result", [])
            if not result:
                raise DataUnavailableError(f"No quote data for {symbol}")
            meta = result[0].get("meta", {})
            return Quote(
                symbol=symbol,
                price=meta.get("regularMarketPrice", 0.0),
                change=meta.get("regularMarketPrice", 0.0) - meta.get("previousClose", 0.0),
                change_pct=(
                    (meta.get("regularMarketPrice", 0.0) / meta.get("previousClose", 1.0)) - 1
                )
                * 100
                if meta.get("previousClose")
                else 0.0,
                volume=meta.get("regularMarketVolume", 0.0),
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            raise DataUnavailableError(f"{self.name} quote failed: {e}") from e

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        yf_symbol = (
            Instrument.normalize_symbol(symbol) + ".NS"
            if not symbol.endswith(".NS") and "^" not in symbol and "=" not in symbol
            else symbol
        )
        y_interval = _YF_INTERVAL_MAP[interval]
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}?period1={start_ts}&period2={end_ts}&interval={y_interval}"
        try:
            data = await self._fetch(url)
            result = data.get("chart", {}).get("result", [])
            if not result:
                return []

            res = result[0]
            timestamps = res.get("timestamp", [])
            if not timestamps:
                return []

            indicators = res.get("indicators", {}).get("quote", [{}])[0]
            opens = indicators.get("open", [])
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            closes = indicators.get("close", [])
            volumes = indicators.get("volume", [])

            bars = []
            for i, ts in enumerate(timestamps):
                if opens[i] is None or closes[i] is None:
                    continue
                bars.append(
                    OHLCVBar(
                        time=datetime.fromtimestamp(ts, tz=UTC),
                        open=float(opens[i]),
                        high=float(highs[i]),
                        low=float(lows[i]),
                        close=float(closes[i]),
                        volume=float(volumes[i]) if volumes[i] is not None else 0.0,
                        adjusted_close=float(closes[i]),
                        interval=interval,
                    )
                )
            return bars
        except Exception as e:
            raise DataUnavailableError(f"{self.name} ohlcv failed for {symbol}: {e}") from e

    async def get_universe(self) -> list[dict]:
        # yfinance doesn't have a specific universe endpoint, return empty or implement a fallback
        return []

    async def health(self) -> dict:
        try:
            await self.get_quote("^NSEI")
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
