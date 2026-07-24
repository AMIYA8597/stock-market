import asyncio
import logging

import httpx
import redis
import yfinance as yf
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Redis client with fallback to in‑memory cache if Redis unavailable
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as exc:
    logger.warning("Redis unavailable (%s); using in‑memory cache.", exc)
    redis_client = None  # type: ignore
# Simple in‑memory cache as a fallback
_in_memory_cache: dict[str, tuple[float, str]] = {}


class Candle(BaseModel):
    timestamp: int  # UNIX epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider:
    """Fetch OHLCV data with fallback and caching.

    Order of providers:
    1️⃣ yfinance
    2️⃣ NSE (via public JSON endpoint)
    3️⃣ Twelve Data (free tier)
    """

    CACHE_TTL = 30  # seconds
    RETRY_ATTEMPTS = 3
    RETRY_BACKOFF = 1  # seconds

    @classmethod
    async def get_candle(
        cls, symbol: str, interval: str = "1d", period: str = "1mo"
    ) -> list[Candle]:
        """Return a list of Candle objects for the requested symbol.

        Results are cached per `symbol|interval|period`.
        """
        cache_key = f"market:{symbol}:{interval}:{period}"
        # Attempt to retrieve from Redis if available, otherwise from in‑memory cache
        cached = None
        if redis_client:
            cached = redis_client.get(cache_key)
        else:
            entry = _in_memory_cache.get(cache_key)
            if entry:
                expiry, raw = entry
                if expiry > asyncio.get_event_loop().time():
                    cached = raw
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            try:
                raw = eval(cached)  # stored as list of dicts
                return [Candle(**c) for c in raw]
            except Exception as exc:
                logger.warning("Failed to parse cached data: %s", exc)

        providers = [cls._fetch_yfinance, cls._fetch_nse, cls._fetch_twelvedata]
        for provider in providers:
            try:
                candles = await provider(symbol, interval, period)
                if candles:
                    # Store in Redis if available, else in‑memory cache with expiry timestamp
                    if redis_client:
                        redis_client.setex(
                            cache_key, cls.CACHE_TTL, str([c.dict() for c in candles])
                        )
                    else:
                        expiry = asyncio.get_event_loop().time() + cls.CACHE_TTL
                        _in_memory_cache[cache_key] = (expiry, str([c.dict() for c in candles]))
                    return candles
            except Exception as exc:
                logger.error("Provider %s failed for %s: %s", provider.__name__, symbol, exc)
                continue
        raise RuntimeError(f"All market data providers failed for {symbol}")

    @staticmethod
    async def _fetch_yfinance(symbol: str, interval: str, period: str) -> list[Candle]:
        async def _call():
            ticker = yf.Ticker(symbol)
            df = ticker.history(interval=interval, period=period)
            if df.empty:
                raise ValueError("No data from yfinance")
            candles = []
            for idx, row in df.iterrows():
                candles.append(
                    Candle(
                        timestamp=int(idx.timestamp()),
                        open=row["Open"],
                        high=row["High"],
                        low=row["Low"],
                        close=row["Close"],
                        volume=row["Volume"],
                    )
                )
            return candles

        return await MarketDataProvider._retry(_call)

    @staticmethod
    async def _fetch_nse(symbol: str, interval: str, period: str) -> list[Candle]:
        async def _call():
            url = f"https://api.nseindia.com/api/quote-equity?symbol={symbol}&series=EQ"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                candles = []
                for item in data.get("data", []):
                    candles.append(
                        Candle(
                            timestamp=int(item.get("timestamp")),
                            open=float(item.get("open")),
                            high=float(item.get("high")),
                            low=float(item.get("low")),
                            close=float(item.get("lastPrice")),
                            volume=float(item.get("quantityTraded", 0)),
                        )
                    )
                return candles

        return await MarketDataProvider._retry(_call)

    @staticmethod
    async def _fetch_twelvedata(symbol: str, interval: str, period: str) -> list[Candle]:
        api_key = settings.TWELVE_DATA_API_KEY

        async def _call():
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": symbol,
                "interval": interval,
                "outputsize": period,
                "apikey": api_key,
                "timezone": "UTC",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if "values" not in data:
                    raise ValueError("Twelve Data returned no values")
                candles = []
                for item in data["values"]:
                    # datetime format: "2023-09-01 09:15:00"
                    dt = item["datetime"].replace("-", "").replace(" ", "").replace(":", "")
                    candles.append(
                        Candle(
                            timestamp=int(dt),
                            open=float(item["open"]),
                            high=float(item["high"]),
                            low=float(item["low"]),
                            close=float(item["close"]),
                            volume=float(item.get("volume", 0)),
                        )
                    )
                return candles

        return await MarketDataProvider._retry(_call)

    @staticmethod
    async def _retry(func, attempts: int = None, backoff: int = None):
        attempts = attempts or MarketDataProvider.RETRY_ATTEMPTS
        backoff = backoff or MarketDataProvider.RETRY_BACKOFF
        for attempt in range(1, attempts + 1):
            try:
                return await func()
            except Exception as exc:
                if attempt == attempts:
                    raise
                logger.warning("Retry %s/%s after error: %s", attempt, attempts, exc)
                await asyncio.sleep(backoff * attempt)
        raise RuntimeError("Retry exhausted")
