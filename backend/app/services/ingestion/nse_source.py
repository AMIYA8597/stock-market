"""NSE India market data provider."""

import asyncio
import csv
import io
import logging
import time
from datetime import UTC, datetime

import aiohttp
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models.instrument import Instrument
from app.services.ingestion.base import (
    DataUnavailableError,
    Interval,
    MarketDataProvider,
    OHLCVBar,
    Quote,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)


class NSESource(MarketDataProvider):
    """NSE India provider implementation."""

    name = "nse"
    _base_url = "https://www.nseindia.com/api/historical/cm/equity"
    _session: aiohttp.ClientSession | None = None
    _last_request_time: float = 0.0
    _lock = asyncio.Lock()

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.nseindia.com/",
        }

    async def _throttle(self):
        """Throttle requests to <= 3 per second."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < 0.34:  # ~3 req per sec
                await asyncio.sleep(0.34 - elapsed)
            self._last_request_time = time.time()

    async def _bootstrap_session(self):
        if self._session is not None:
            await self._session.close()
        self._session = aiohttp.ClientSession(timeout=self.timeout, headers=self.headers)
        await self._throttle()
        try:
            async with self._session.get("https://www.nseindia.com") as response:
                if response.status in (401, 403):
                    raise RateLimitExceededError(f"NSE bootstrap forbidden: {response.status}")
                if response.status >= 400:
                    raise DataUnavailableError(f"NSE bootstrap failed: {response.status}")
                # Session now has cookies
        except Exception as e:
            if self._session:
                await self._session.close()
                self._session = None
            raise DataUnavailableError(f"Failed to bootstrap NSE session: {e}")

    @retry(
        retry=retry_if_exception_type(
            (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                DataUnavailableError,
                RateLimitExceededError,
            )
        ),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch(self, url: str, params: dict = None, return_json: bool = True) -> any:
        if self._session is None:
            await self._bootstrap_session()

        await self._throttle()
        headers = self.headers.copy()
        headers["accept"] = "*/*"

        try:
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status in (401, 403):
                    logger.info("NSE session expired, re-bootstrapping...")
                    await self._bootstrap_session()
                    raise RateLimitExceededError("NSE session expired or forbidden")
                if response.status == 429:
                    raise RateLimitExceededError("NSE rate limit exceeded")
                if response.status >= 400:
                    raise DataUnavailableError(f"NSE returned {response.status} for {url}")

                if return_json:
                    return await response.json()
                return await response.text()
        except aiohttp.ClientError as e:
            raise DataUnavailableError(f"NSE network error: {e}")

    def _map_symbol(self, symbol: str) -> str:
        # NSE expects clean symbol, e.g. RELIANCE, sometimes quote URL escapes it
        return Instrument.normalize_symbol(symbol)

    async def get_quote(self, symbol: str) -> Quote:
        clean_symbol = self._map_symbol(symbol)
        url = "https://www.nseindia.com/api/quote-equity"
        try:
            import urllib.parse

            data = await self._fetch(url, params={"symbol": urllib.parse.quote(clean_symbol)})
            price_info = data.get("priceInfo", {})
            if not price_info:
                raise DataUnavailableError(f"No price info for {symbol}")

            return Quote(
                symbol=symbol,
                price=float(price_info.get("lastPrice", 0.0)),
                change=float(price_info.get("change", 0.0)),
                change_pct=float(price_info.get("pChange", 0.0)),
                volume=float(
                    data.get("preOpenMarket", {}).get("totalTradedVolume", 0.0)
                ),  # Fallback to preopen volume if main not present in priceInfo
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            raise DataUnavailableError(f"NSE quote failed for {symbol}: {e}")

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        if interval != "1d":
            # Real NSE historical API only reliably provides daily in this endpoint
            return []

        clean_symbol = self._map_symbol(symbol)
        params = {
            "symbol": clean_symbol,
            "from": start.strftime("%d-%m-%Y"),
            "to": end.strftime("%d-%m-%Y"),
            "series": '["EQ"]',
        }

        try:
            payload = await self._fetch(self._base_url, params=params)
            rows = payload.get("data", [])
            bars = []
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
        except Exception as e:
            raise DataUnavailableError(f"NSE OHLCV failed for {symbol}: {e}")

    async def get_universe(self) -> list[dict]:
        """Fetch NSE equity master"""
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        try:
            # We don't use the standard _fetch as this is on archives.nseindia.com, doesn't need session bootstrap
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status >= 400:
                        raise DataUnavailableError(
                            f"Failed to fetch NSE universe: {response.status}"
                        )
                    csv_data = await response.text()

            f = io.StringIO(csv_data)
            reader = csv.DictReader(f)
            universe = []
            for row in reader:
                symbol = row.get("SYMBOL")
                name = row.get("NAME OF COMPANY")
                if symbol and name:
                    universe.append(
                        {
                            "symbol": symbol,
                            "display_name": name,
                            "exchange": "NSE",
                            "yfinance_ticker": f"{symbol}.NS",
                        }
                    )
            return universe
        except Exception as e:
            raise DataUnavailableError(f"NSE universe fetch failed: {e}")

    async def health(self) -> dict:
        try:
            await self._bootstrap_session()
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None
