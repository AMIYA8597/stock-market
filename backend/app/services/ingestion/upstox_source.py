"""Upstox market data provider (free, read-only Analytics Token).

Uses the Analytics Token (Upstox Developer -> Analytics): free, read-only,
one-year validity, covers Market Quote / Historical Data / WebSocket, and
cannot place or modify orders. This is a separate credential from
UPSTOX_API_KEY/SECRET (the OAuth broker-trading flow) - see
app/core/config.py.

Symbol resolution goes through the existing Instrument/InstrumentAlias
tables (provider="upstox", alias_type="instrument_key"), not a hardcoded
dict - that mapping is populated by a separate instrument-master sync job
(not yet implemented; see the migration plan). Until an instrument has a
row there, this provider honestly raises DataUnavailableError for it
rather than guessing an instrument_key.

NOTE ON RESPONSE PARSING: the exact JSON field names below follow
Upstox's documented V3 response shape, but have not been verified against
a live call - this environment has no network route to api.upstox.com
(confirmed: the egress proxy rejects it, same restriction that already
applies to Yahoo Finance and the real Supabase DB in this sandbox). The
first real call made with an actual Analytics Token should be checked
against these field names and this comment removed once confirmed.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.ingestion.base import (
    DataUnavailableError,
    Interval,
    MarketDataProvider,
    OHLCVBar,
    ProviderError,
    Quote,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)

# Interval -> (unit, interval) for Upstox's V3 historical-candle path:
# GET /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
_INTERVAL_MAP: dict[Interval, tuple[str, str]] = {
    "1m": ("minutes", "1"),
    "5m": ("minutes", "5"),
    "15m": ("minutes", "15"),
    "1h": ("hours", "1"),
    "1d": ("days", "1"),
}


class UpstoxAuthError(ProviderError):
    """Raised on 401/403 - the Analytics Token is missing, expired, or invalid."""


async def _resolve_instrument_key(symbol: str) -> str:
    """Look up the Upstox instrument_key for a canonical symbol via InstrumentAlias.

    Raises DataUnavailableError (not a KeyError or silent fallback) if no
    mapping exists yet - this is expected and honest until the instrument-
    master sync job (separate, not yet built) has populated the table.
    """
    from sqlalchemy import select

    from app.database.connection import async_session_factory
    from app.models.market import Instrument, InstrumentAlias

    async with async_session_factory() as db:
        result = await db.execute(
            select(InstrumentAlias.provider_symbol)
            .join(Instrument, Instrument.id == InstrumentAlias.instrument_id)
            .where(
                Instrument.canonical_symbol == symbol,
                InstrumentAlias.provider == "upstox",
                InstrumentAlias.alias_type == "instrument_key",
            )
        )
        row = result.scalars().first()
        if not row:
            raise DataUnavailableError(
                f"No Upstox instrument_key mapped for {symbol!r} yet "
                "(instrument-master sync has not run for this symbol)."
            )
        return row


class UpstoxSource(MarketDataProvider):
    """Upstox V3 REST provider implementation."""

    name = "upstox"

    def __init__(self, token: str | None = None, base_url: str | None = None, timeout: int = 15):
        from app.core.config import get_settings

        settings = get_settings()
        self.token = token if token is not None else settings.UPSTOX_ANALYTICS_TOKEN
        self.base_url = (base_url or settings.UPSTOX_BASE_URL).rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise UpstoxAuthError("UPSTOX_ANALYTICS_TOKEN is not configured.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=self._headers(), params=params) as response:
                if response.status in (401, 403):
                    raise UpstoxAuthError(
                        f"Upstox rejected the Analytics Token (HTTP {response.status})."
                    )
                if response.status == 429:
                    raise RateLimitExceededError(f"{self.name} rate limit exceeded.")
                if response.status >= 400:
                    body = await response.text()
                    raise DataUnavailableError(
                        f"{self.name} returned HTTP {response.status}: {body[:200]}"
                    )
                return await response.json()

    async def get_quote(self, symbol: str) -> Quote:
        instrument_key = await _resolve_instrument_key(symbol)
        try:
            payload = await self._get(
                "/v3/market-quote/ohlc",
                params={"instrument_key": instrument_key, "interval": "1d"},
            )
            data = payload.get("data", {})
            entry = data.get(instrument_key) or next(iter(data.values()), None)
            if not entry:
                raise DataUnavailableError(f"No OHLC entry for {symbol} in Upstox response")

            live = entry.get("live_ohlc", {})
            prev = entry.get("prev_ohlc", {})
            price = float(live.get("close") or entry.get("last_price") or 0.0)
            prev_close = float(prev.get("close") or 0.0)

            return Quote(
                symbol=symbol,
                price=price,
                change=price - prev_close if prev_close else 0.0,
                change_pct=((price / prev_close) - 1) * 100 if prev_close else 0.0,
                volume=float(live.get("volume") or 0.0),
                timestamp=datetime.now(UTC),
            )
        except (UpstoxAuthError, RateLimitExceededError, DataUnavailableError):
            raise
        except Exception as e:
            raise DataUnavailableError(f"{self.name} quote failed for {symbol}: {e}") from e

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        if interval not in _INTERVAL_MAP:
            raise DataUnavailableError(f"{self.name} does not support interval {interval!r}")

        instrument_key = await _resolve_instrument_key(symbol)
        unit, upstox_interval = _INTERVAL_MAP[interval]
        from_date = start.date() if isinstance(start, datetime) else start
        to_date = end.date() if isinstance(end, datetime) else end

        try:
            payload = await self._get(
                f"/v3/historical-candle/{instrument_key}/{unit}/{upstox_interval}"
                f"/{to_date.isoformat()}/{from_date.isoformat()}"
            )
            candles = payload.get("data", {}).get("candles", [])

            bars: list[OHLCVBar] = []
            for candle in candles:
                # Documented shape: [timestamp, open, high, low, close, volume, open_interest]
                ts_str, o, h, low, c, vol = candle[0], candle[1], candle[2], candle[3], candle[4], candle[5]
                bars.append(
                    OHLCVBar(
                        time=datetime.fromisoformat(ts_str),
                        open=float(o),
                        high=float(h),
                        low=float(low),
                        close=float(c),
                        volume=float(vol or 0.0),
                        adjusted_close=None,
                        interval=interval,
                    )
                )
            bars.sort(key=lambda b: b.time)
            return bars
        except (UpstoxAuthError, RateLimitExceededError, DataUnavailableError):
            raise
        except Exception as e:
            raise DataUnavailableError(f"{self.name} ohlcv failed for {symbol}: {e}") from e

    async def get_universe(self) -> list[dict]:
        # Instrument-master sync (the real source of the trading universe
        # for this provider) is a separate job, not yet implemented - see
        # the migration plan's upstox_instrument_tasks.py. Returning []
        # here is the honest current state, matching StooqProvider's same
        # pattern, rather than fabricating a universe list.
        return []

    async def health(self) -> dict:
        if not self.token:
            return {"status": "down", "provider": self.name, "error": "UPSTOX_ANALYTICS_TOKEN not configured"}
        try:
            await self.get_quote("RELIANCE")
            return {"status": "ok", "provider": self.name}  # honesty: allow (only reached after a real successful probe above)
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
