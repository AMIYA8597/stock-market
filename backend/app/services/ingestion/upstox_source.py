"""Upstox market data provider (free, read-only Analytics Token).

Uses the Analytics Token (Upstox Developer -> Analytics): free, read-only,
covers Market Quote / Historical Data / WebSocket, and cannot place or
modify orders. This is a separate credential from UPSTOX_API_KEY/SECRET
(the OAuth broker-trading flow) - see app/core/config.py.

Symbol resolution: DB InstrumentAlias first, then Upstox search API
auto-discovery, then a built-in NSE top-100 instrument_key map.
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

# Hardcoded NSE instrument keys for Nifty 100 stocks + indices.
# These are stable ISIN-based keys that rarely change.
_NSE_HARDCODED_KEYS: dict[str, str] = {
    # Nifty 50
    "RELIANCE":     "NSE_EQ|INE002A01018",
    "TCS":          "NSE_EQ|INE467B01029",
    "HDFCBANK":     "NSE_EQ|INE040A01034",
    "INFY":         "NSE_EQ|INE009A01021",
    "ICICIBANK":    "NSE_EQ|INE090A01021",
    "HINDUNILVR":   "NSE_EQ|INE030A01027",
    "BAJFINANCE":   "NSE_EQ|INE296A01024",
    "WIPRO":        "NSE_EQ|INE075A01022",
    "KOTAKBANK":    "NSE_EQ|INE237A01028",
    "LT":           "NSE_EQ|INE018A01030",
    "ASIANPAINT":   "NSE_EQ|INE021A01026",
    "MARUTI":       "NSE_EQ|INE585B01010",
    "AXISBANK":     "NSE_EQ|INE238A01034",
    "TITAN":        "NSE_EQ|INE280A01028",
    "SUNPHARMA":    "NSE_EQ|INE044A01036",
    "ULTRACEMCO":   "NSE_EQ|INE481G01011",
    "BAJAJFINSV":   "NSE_EQ|INE918I01026",
    "NESTLEIND":    "NSE_EQ|INE239A01024",
    "TECHM":        "NSE_EQ|INE669C01036",
    "HCLTECH":      "NSE_EQ|INE860A01027",
    "MM":           "NSE_EQ|INE101A01026",
    "TATAMOTORS":   "NSE_EQ|INE155A01022",
    "BHARTIARTL":   "NSE_EQ|INE397D01024",
    "ITC":          "NSE_EQ|INE154A01025",
    "ONGC":         "NSE_EQ|INE213A01029",
    "COALINDIA":    "NSE_EQ|INE522F01014",
    "NTPC":         "NSE_EQ|INE733E01010",
    "POWERGRID":    "NSE_EQ|INE752E01010",
    "INDUSINDBK":   "NSE_EQ|INE095A01012",
    "SBIN":         "NSE_EQ|INE062A01020",
    "DRREDDY":      "NSE_EQ|INE089A01023",
    "CIPLA":        "NSE_EQ|INE059A01026",
    "DIVISLAB":     "NSE_EQ|INE361B01024",
    "EICHERMOT":    "NSE_EQ|INE066A01021",
    "HEROMOTOCO":   "NSE_EQ|INE158A01026",
    "GRASIM":       "NSE_EQ|INE047A01021",
    "BRITANNIA":    "NSE_EQ|INE216A01030",
    "ADANIPORTS":   "NSE_EQ|INE742F01042",
    "BPCL":         "NSE_EQ|INE029A01011",
    "TATACONSUM":   "NSE_EQ|INE192A01025",
    "JSWSTEEL":     "NSE_EQ|INE019A01038",
    "TATASTEEL":    "NSE_EQ|INE081A01020",
    "HINDALCO":     "NSE_EQ|INE038A01020",
    "APOLLOHOSP":   "NSE_EQ|INE437A01024",
    "ADANIENT":     "NSE_EQ|INE423A01024",
    "SHREECEM":     "NSE_EQ|INE070A01015",
    "UPL":          "NSE_EQ|INE628A01036",
    # Nifty Next 50
    "DABUR":        "NSE_EQ|INE016A01026",
    "BAJAJ-AUTO":   "NSE_EQ|INE917I01010",
    "BAJAJ_AUTO":   "NSE_EQ|INE917I01010",
    "BAJAJAUTO":    "NSE_EQ|INE917I01010",
    "SIEMENS":      "NSE_EQ|INE003A01024",
    "BERGEPAINT":   "NSE_EQ|INE463A01038",
    "TRENT":        "NSE_EQ|INE849A01020",
    "ICICIGI":      "NSE_EQ|INE765G01017",
    "ICICIPRULI":   "NSE_EQ|INE726G01019",
    "SBICARD":      "NSE_EQ|INE018E01016",
    "HDFCLIFE":     "NSE_EQ|INE795G01014",
    "SBILIFE":      "NSE_EQ|INE123W01016",
    "PIDILITIND":   "NSE_EQ|INE318A01026",
    "GODREJCP":     "NSE_EQ|INE102D01028",
    "PGHH":         "NSE_EQ|INE179A01014",
    "COLPAL":       "NSE_EQ|INE259A01022",
    "TORNTPHARM":   "NSE_EQ|INE685A01028",
    "LUPIN":        "NSE_EQ|INE326A01037",
    "BIOCON":       "NSE_EQ|INE376G01013",
    "AUROPHARMA":   "NSE_EQ|INE406A01037",
    "MUTHOOTFIN":   "NSE_EQ|INE414G01012",
    "CHOLAFIN":     "NSE_EQ|INE121A01024",
    "MOTHERSON":    "NSE_EQ|INE775I01017",
    "BOSCHLTD":     "NSE_EQ|INE323A01026",
    "HAVELLS":      "NSE_EQ|INE176B01034",
    "TATAPOWER":    "NSE_EQ|INE245A01021",
    "INDUSTOWER":   "NSE_EQ|INE121J01017",
    "ATGL":         "NSE_EQ|INE399L01023",
    "AMBUJACEM":    "NSE_EQ|INE079A01024",
    "ACC":          "NSE_EQ|INE012A01025",
    "NAUKRI":       "NSE_EQ|INE663F01024",
    "DLF":          "NSE_EQ|INE271C01023",
    "MCDOWELL-N":   "NSE_EQ|INE854D01024",
    "PFC":          "NSE_EQ|INE134E01011",
    "RECLTD":       "NSE_EQ|INE020B01018",
    "GAIL":         "NSE_EQ|INE129A01019",
    "IOC":          "NSE_EQ|INE242A01010",
    "HINDPETRO":    "NSE_EQ|INE094A01015",
    "VEDL":         "NSE_EQ|INE205A01025",
    "ZOMATO":       "NSE_EQ|INE758T01015",
    "PAYTM":        "NSE_EQ|INE982J01020",
    "NYKAA":        "NSE_EQ|INE388Y01029",
    "POLICYBZR":    "NSE_EQ|INE417T01026",
    "LTI":          "NSE_EQ|INE214T01019",
    "LTIM":         "NSE_EQ|INE214T01019",
    "MPHASIS":      "NSE_EQ|INE356A01018",
    "OFSS":         "NSE_EQ|INE881D01027",
    "PERSISTENT":   "NSE_EQ|INE262H01021",
    "COFORGE":      "NSE_EQ|INE591G01017",
    "TANLA":        "NSE_EQ|INE483C01032",
    "JUBLFOOD":     "NSE_EQ|INE797F01020",
    "DMART":        "NSE_EQ|INE192R01011",
    "PHOENIXLTD":   "NSE_EQ|INE484J01027",
    "CROMPTON":     "NSE_EQ|INE299U01018",
    # Indices
    "^NSEI":        "NSE_INDEX|Nifty 50",
    "^NSEBANK":     "NSE_INDEX|Nifty Bank",
    "^BSESN":       "BSE_INDEX|SENSEX",
}

# In-memory cache to avoid repeated DB lookups
_instrument_key_cache: dict[str, str] = {}

# Interval -> (unit, interval) for Upstox's V3 historical-candle path:
# GET /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
_INTERVAL_MAP: dict[Interval, tuple[str, str]] = {
    "1m": ("minutes", "1"),
    "5m": ("minutes", "5"),
    "15m": ("minutes", "15"),
    "30m": ("minutes", "30"),
    "1h": ("hours", "1"),
    "1d": ("days", "1"),
    "1w": ("weeks", "1"),
    "1mo": ("months", "1"),
}


class UpstoxAuthError(ProviderError):
    """Raised on 401/403 - the Analytics Token is missing, expired, or invalid."""


async def _search_upstox_instrument_key(symbol: str, token: str, base_url: str) -> str | None:
    """Query Upstox search API to find instrument_key for a symbol."""
    try:
        url = f"{base_url}/v2/instruments/search"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"query": symbol}, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                instruments = data.get("data", []) if isinstance(data, dict) else []
                # Find best match: exact NSE EQ match for the symbol
                for inst in instruments:
                    ts = inst.get("trading_symbol", "").upper()
                    exchange = inst.get("exchange", "").upper()
                    ikey = inst.get("instrument_key", "")
                    if ts == symbol.upper() and exchange == "NSE" and "EQ" in ikey:
                        return ikey
                # Fallback: first NSE result
                for inst in instruments:
                    if inst.get("exchange", "").upper() == "NSE":
                        ikey = inst.get("instrument_key", "")
                        if ikey:
                            return ikey
                return None
    except Exception as e:
        logger.debug(f"Upstox instrument search failed for {symbol}: {e}")
        return None


async def _resolve_instrument_key(symbol: str, token: str | None = None, base_url: str | None = None) -> str:
    """Resolve Upstox instrument_key for a canonical symbol.

    Resolution order:
    1. In-memory cache
    2. Hardcoded map (NSE top 100 + indices)
    3. DB InstrumentAlias table
    4. Upstox search API (auto-discovery, stores result in DB)

    Raises DataUnavailableError if all sources fail.
    """
    sym = symbol.upper()

    # 1. Memory cache
    if sym in _instrument_key_cache:
        return _instrument_key_cache[sym]

    # 2. Hardcoded map — covers Nifty 100 instantly without any I/O
    if sym in _NSE_HARDCODED_KEYS:
        key = _NSE_HARDCODED_KEYS[sym]
        _instrument_key_cache[sym] = key
        return key

    # 3. DB lookup
    try:
        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import Instrument, InstrumentAlias

        async with async_session_factory() as db:
            result = await db.execute(
                select(InstrumentAlias.provider_symbol)
                .join(Instrument, Instrument.id == InstrumentAlias.instrument_id)
                .where(
                    Instrument.canonical_symbol == sym,
                    InstrumentAlias.provider == "upstox",
                    InstrumentAlias.alias_type == "instrument_key",
                )
            )
            row = result.scalars().first()
            if row:
                _instrument_key_cache[sym] = row
                return row
    except Exception as e:
        logger.debug(f"DB instrument key lookup failed for {sym}: {e}")

    # 4. Upstox search API auto-discovery
    if token:
        found_key = await _search_upstox_instrument_key(sym, token, base_url or "https://api.upstox.com")
        if found_key:
            _instrument_key_cache[sym] = found_key
            # Best-effort persist to DB for future calls
            try:
                from sqlalchemy import select

                from app.database.connection import async_session_factory
                from app.models.market import Instrument, InstrumentAlias

                async with async_session_factory() as db:
                    inst_res = await db.execute(
                        select(Instrument).where(Instrument.canonical_symbol == sym)
                    )
                    inst = inst_res.scalars().first()
                    if inst:
                        alias = InstrumentAlias(
                            instrument_id=inst.id,
                            provider="upstox",
                            provider_symbol=found_key,
                            alias_type="instrument_key",
                        )
                        db.add(alias)
                        await db.commit()
            except Exception as e:
                logger.debug(f"Failed to persist instrument key for {sym}: {e}")
            return found_key

    raise DataUnavailableError(
        f"No Upstox instrument_key found for {symbol!r}. "
        "Not in hardcoded map, DB, or Upstox search results."
    )


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
        instrument_key = await _resolve_instrument_key(symbol, self.token, self.base_url)
        try:
            payload = await self._get(
                "/v3/market-quote/ohlc",
                params={"instrument_key": instrument_key, "interval": "1d"},
            )
            if not payload or not isinstance(payload, dict):
                raise DataUnavailableError(f"Empty Upstox response for {symbol}")
            data = payload.get("data") or {}
            entry = data.get(instrument_key) or next(iter(data.values()), None)
            if not entry:
                raise DataUnavailableError(f"No OHLC entry for {symbol} in Upstox response")

            live = entry.get("live_ohlc") or entry.get("ohlc") or {}
            prev = entry.get("prev_ohlc") or {}
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

        instrument_key = await _resolve_instrument_key(symbol, self.token, self.base_url)
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
