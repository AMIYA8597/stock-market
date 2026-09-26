"""Binance market data provider -- real crypto/token market data.

Uses Binance's public REST API (https://api.binance.com), which requires
no API key for market data (quotes, candles, the tradable-symbol list).
An API key is only needed to place real orders on Binance, which this
provider does not do -- it is read-only, matching the other providers in
this package.
"""

import asyncio
import logging
from datetime import UTC, datetime

import aiohttp

from app.services.ingestion.base import (
    DataUnavailableError,
    Interval,
    MarketDataProvider,
    OHLCVBar,
    Quote,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.binance.com"

# Binance's kline interval strings happen to match this project's Interval
# literal exactly for every value we support (1m/5m/15m/1h/1d), so no
# translation table is needed the way yfinance's is.
_MAX_KLINES_PER_REQUEST = 1000


class BinanceSource(MarketDataProvider):
    """Binance spot market provider implementation."""

    name = "binance"

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def _get_json(self, path: str, params: dict | None = None):
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(f"{_BASE_URL}{path}", params=params) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise DataUnavailableError(
                        f"Binance request failed ({response.status}): {body[:200]}"
                    )
                return await response.json()

    async def get_quote(self, symbol: str) -> Quote:
        sym = symbol.upper().replace("/", "").replace("-", "")
        try:
            data = await self._get_json("/api/v3/ticker/24hr", params={"symbol": sym})
            price = float(data["lastPrice"])
            change = float(data["priceChange"])
            change_pct = float(data["priceChangePercent"])
            volume = float(data["volume"])
            return Quote(
                symbol=sym,
                price=price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                timestamp=datetime.now(UTC),
            )
        except DataUnavailableError:
            raise
        except Exception as e:
            raise DataUnavailableError(f"{self.name} quote failed for {symbol}: {e}") from e

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        sym = symbol.upper().replace("/", "").replace("-", "")
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        bars: list[OHLCVBar] = []
        cursor = start_ms
        try:
            while cursor < end_ms:
                klines = await self._get_json(
                    "/api/v3/klines",
                    params={
                        "symbol": sym,
                        "interval": interval,
                        "startTime": cursor,
                        "endTime": end_ms,
                        "limit": _MAX_KLINES_PER_REQUEST,
                    },
                )
                if not klines:
                    break

                for k in klines:
                    open_time_ms, o, h, l, c, v = k[0], k[1], k[2], k[3], k[4], k[5]
                    bars.append(
                        OHLCVBar(
                            time=datetime.fromtimestamp(open_time_ms / 1000, tz=UTC),
                            open=float(o),
                            high=float(h),
                            low=float(l),
                            close=float(c),
                            volume=float(v),
                            adjusted_close=float(c),
                            interval=interval,
                        )
                    )

                last_open_time = klines[-1][0]
                if len(klines) < _MAX_KLINES_PER_REQUEST or last_open_time <= cursor:
                    break
                cursor = last_open_time + 1
                await asyncio.sleep(0.2)  # stay well under Binance's rate limit

            return bars
        except DataUnavailableError:
            raise
        except Exception as e:
            raise DataUnavailableError(f"{self.name} ohlcv failed for {symbol}: {e}") from e

    async def get_universe(self) -> list[dict]:
        """All actively trading USDT-quoted spot pairs -- the most liquid,
        commonly tradeable slice of Binance's several thousand listed pairs.
        """
        try:
            data = await self._get_json("/api/v3/exchangeInfo")
            universe = []
            for s in data.get("symbols", []):
                if s.get("status") != "TRADING":
                    continue
                if s.get("quoteAsset") != "USDT":
                    continue
                if not s.get("isSpotTradingAllowed", True):
                    continue
                universe.append(
                    {
                        "symbol": s["symbol"],
                        "display_name": f"{s['baseAsset']}/{s['quoteAsset']}",
                        "exchange": "BINANCE",
                        "base_asset": s["baseAsset"],
                        "quote_asset": s["quoteAsset"],
                    }
                )
            return universe
        except DataUnavailableError:
            raise
        except Exception as e:
            raise DataUnavailableError(f"{self.name} universe fetch failed: {e}") from e

    async def health(self) -> dict:
        try:
            await self._get_json("/api/v3/ping")
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
