"""Stooq market data provider."""

import asyncio
import csv
import io
import logging
from datetime import UTC, datetime

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


class StooqProvider(MarketDataProvider):
    """Stooq provider implementation."""

    name = "stooq"

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
    async def _fetch_csv(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    raise RateLimitExceededError(f"{self.name} rate limit exceeded.")
                if response.status >= 400:
                    raise DataUnavailableError(f"{self.name} returned {response.status}")
                return await response.text()

    def _map_symbol(self, symbol: str) -> str:
        stooq_symbol = Instrument.normalize_symbol(symbol).upper()
        if symbol.endswith(".NS"):
            return f"{stooq_symbol}.IN"
        if "." not in symbol and symbol not in ("^NSEI", "^BSESN"):
            return f"{stooq_symbol}.US"
        return stooq_symbol

    async def get_quote(self, symbol: str) -> Quote:
        # Stooq doesn't provide a direct JSON quote API. We parse the latest daily bar.
        stooq_symbol = self._map_symbol(symbol)
        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&f=sd2t2ohlcv&a=dn"
        try:
            csv_data = await self._fetch_csv(url)
            f = io.StringIO(csv_data)
            reader = list(csv.DictReader(f))
            if not reader or "Date" not in reader[0]:
                raise DataUnavailableError(f"No quote data for {symbol}")

            row = reader[0]
            price = float(row["Close"])
            # We don't have previous close easily without looking at row[1], assuming reader has at least 2
            prev_price = float(reader[1]["Close"]) if len(reader) > 1 else price

            return Quote(
                symbol=symbol,
                price=price,
                change=price - prev_price,
                change_pct=((price / prev_price) - 1) * 100 if prev_price else 0.0,
                volume=float(row.get("Volume", 0.0) or 0.0),
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            raise DataUnavailableError(f"{self.name} quote failed: {e}") from e

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        if interval != "1d":
            # Stooq free CSV endpoint only supports daily data
            return []

        stooq_symbol = self._map_symbol(symbol)
        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&f=sd2t2ohlcv&a=dn"

        try:
            csv_data = await self._fetch_csv(url)
            f = io.StringIO(csv_data)
            reader = csv.DictReader(f)

            if not reader.fieldnames or "Date" not in reader.fieldnames:
                return []

            bars: list[OHLCVBar] = []
            for row in reader:
                try:
                    dt = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=UTC)
                    start_tz = (
                        start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
                    )
                    end_tz = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)

                    if not (start_tz <= dt <= end_tz):
                        continue

                    bars.append(
                        OHLCVBar(
                            time=dt,
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=float(row["Close"]),
                            volume=float(row.get("Volume", 0.0) or 0.0),
                            adjusted_close=None,
                            interval=interval,
                        )
                    )
                except Exception:
                    continue
            bars.reverse()
            return bars
        except Exception as e:
            raise DataUnavailableError(f"{self.name} ohlcv failed for {symbol}: {e}") from e

    async def get_universe(self) -> list[dict]:
        return []

    async def health(self) -> dict:
        try:
            await self.get_quote("^NSEI")
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
