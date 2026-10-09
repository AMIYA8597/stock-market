# backend/app/services/market_data_service.py
"""Market Data Service — Single point of contact for all yfinance data."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime, timedelta

import yfinance as yf

from app.core.logging import get_logger
from app.services.stock_universe import (
    ALL_STOCKS as _ALL_STOCKS,
)
from app.services.stock_universe import (
    INDICES as _INDICES,
)
from app.services.stock_universe import (
    NIFTY_50 as _NIFTY_50,
)
from app.services.stock_universe import (
    NIFTY_NEXT50 as _NIFTY_NEXT50,
)
from app.services.stock_universe import (
    TOP100 as _TOP100,
)

logger = get_logger(__name__)


class HistoryList(list):
    """Subclass of list that carries data source metadata."""

    def __init__(self, items, source: str = "yfinance"):
        super().__init__(items)
        self.source = source


def safe_float(val, fallback=0.0) -> float:
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return fallback
        return f
    except Exception:
        return fallback


import time


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    async def consume(self, tokens: float = 1.0):
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            await asyncio.sleep(0.01)


class MarketDataService:
    # Class-level session and caches for sockets, rate-limiting, and performance optimization
    _session = None
    _semaphore = asyncio.Semaphore(
        20
    )  # limit concurrency to avoid descriptor exhaustion under select()

    # Capacity was 20 — exactly the full watchlist size — so a startup batch
    # fetch could burst all 20 requests to Yahoo Finance simultaneously with
    # zero throttling, which repeatedly triggered Yahoo's rate-limit/block and
    # made every symbol in the batch fail together ("possibly delisted" is
    # yfinance's generic error for a blocked/empty response, not a real
    # delisting). A smaller burst allowance forces real staggering.
    _yfinance_bucket = TokenBucket(rate=5.0, capacity=5.0)
    _nse_bucket = TokenBucket(rate=5.0, capacity=10.0)

    _in_memory_ticker_history_df_cache: dict = {}

    @classmethod
    async def _throttle_yfinance(cls, symbol: str) -> None:
        await cls._yfinance_bucket.consume(1.0)

    @classmethod
    async def _throttle_nse(cls) -> None:
        await cls._nse_bucket.consume(1.0)

    # Stock universe from centralized module (1000+ symbols)
    NSE_NIFTY50 = _NIFTY_50
    NSE_NIFTY_NEXT50 = _NIFTY_NEXT50
    NSE_TOP100 = _TOP100
    NSE_ALL_STOCKS = _ALL_STOCKS
    NSE_INDICES = _INDICES

    @classmethod
    def get_session(cls):
        if cls._session is None:
            import requests
            from requests.adapters import HTTPAdapter

            cls._session = requests.Session()
            cls._session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            # Default urllib3 pool (10 connections) is far smaller than the
            # concurrent yfinance/NSE fetches this app fires for a full
            # watchlist — it was silently discarding excess connections and
            # contributing to request pileup under load ("Connection pool is
            # full, discarding connection" in the logs).
            adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50)
            cls._session.mount("https://", adapter)
            cls._session.mount("http://", adapter)
        return cls._session

    _health_cache: dict | None = None
    _health_cache_at: float = 0.0

    @classmethod
    async def health(cls) -> dict:
        """Lightweight, cached check that the upstream market data provider is reachable."""
        now = datetime.now(UTC).timestamp()
        if cls._health_cache is not None and (now - cls._health_cache_at) < 60:
            return cls._health_cache

        def _probe() -> bool:
            try:
                session = cls.get_session()
                df = yf.download(
                    "^NSEI",
                    period="1d",
                    interval="1d",
                    progress=False,
                    threads=False,
                    session=session,
                )
                return not df.empty
            except Exception:
                return False

        try:
            ok = await asyncio.wait_for(asyncio.to_thread(_probe), timeout=5.0)
        except Exception:
            ok = False

        result = {"status": "ok" if ok else "unhealthy"}  # honesty: allow (conditional on a real probe above)
        cls._health_cache = result
        cls._health_cache_at = now
        return result

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize a user-supplied symbol to its canonical (bare, no
        provider suffix) form used as Instrument.canonical_symbol in the
        canonical DB — e.g. "reliance" -> "RELIANCE", not "RELIANCE.NS".

        Also maps well-known index aliases (NIFTY50, BANKNIFTY, SENSEX) to
        their canonical index tickers.
        """
        s = symbol.upper().strip()

        # Map indices to their correct yfinance tickers
        mappings = {
            "NIFTY50": "^NSEI",
            "NIFTY 50": "^NSEI",
            "NIFTY_50": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "BANK NIFTY": "^NSEBANK",
            "BANK_NIFTY": "^NSEBANK",
            "NSEBANK": "^NSEBANK",
            "SENSEX": "^BSESN",
        }
        if s in mappings:
            return mappings[s]

        # Bypass common US stock tickers to prevent appending
        us_tickers = {
            "AAPL",
            "MSFT",
            "GOOG",
            "GOOGL",
            "TSLA",
            "AMZN",
            "NVDA",
            "META",
            "NFLX",
            "AMD",
            "INTC",
            "QCOM",
            "AVGO",
            "CSCO",
            "PEP",
            "KO",
            "DIS",
        }
        if s in us_tickers:
            return s

        return s

    @staticmethod
    async def get_batch_quotes(symbols: list[str]) -> dict[str, dict]:
        """Fetch quotes for multiple symbols concurrently."""
        import asyncio

        tasks = []
        for sym in symbols:
            tasks.append(MarketDataService.get_quote(sym))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_res = {}
        for sym, res in zip(symbols, results, strict=False):
            if isinstance(res, Exception):
                batch_res[sym] = None
            else:
                batch_res[sym] = res
        return batch_res

    @classmethod
    async def _yfinance_quote(cls, symbol: str) -> dict:
        """Fetch a live quote directly from yfinance."""
        sym = cls._normalize_symbol(symbol)
        yf_sym = sym if sym.startswith("^") or "." in sym else f"{sym}.NS"

        await cls._throttle_yfinance(yf_sym)

        def _fetch():
            session = cls.get_session()
            ticker = yf.Ticker(yf_sym, session=session)
            info = ticker.info or {}
            price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"), 0.0)
            prev_close = safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"), price)
            change = price - prev_close if prev_close else 0.0
            change_pct = (change / prev_close * 100) if prev_close else 0.0
            return {
                "symbol": sym,
                "price": price,
                "open": safe_float(info.get("open") or info.get("regularMarketOpen"), price),
                "high": safe_float(info.get("dayHigh") or info.get("regularMarketDayHigh"), price),
                "low": safe_float(info.get("dayLow") or info.get("regularMarketDayLow"), price),
                "volume": int(safe_float(info.get("volume") or info.get("regularMarketVolume"), 0)),
                "previous_close": prev_close,
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "market_cap": safe_float(info.get("marketCap"), 0.0),
                "week_52_high": safe_float(info.get("fiftyTwoWeekHigh"), price),
                "week_52_low": safe_float(info.get("fiftyTwoWeekLow"), price),
                "source": "yfinance",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        async with cls._semaphore:
            return await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10.0)

    @classmethod
    async def _upstox_quote(cls, symbol: str) -> dict | None:
        """Try Upstox Analytics Token for a live quote. Returns None if unavailable."""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            if not getattr(settings, "UPSTOX_ENABLED", False) or not getattr(settings, "UPSTOX_ANALYTICS_TOKEN", None):
                return None
            from app.services.ingestion.upstox_source import UpstoxSource
            source = UpstoxSource()
            quote = await source.get_quote(symbol)
            return {
                "symbol": cls._normalize_symbol(symbol),
                "price": quote.price,
                "open": quote.price,
                "high": quote.price,
                "low": quote.price,
                "volume": int(quote.volume or 0),
                "previous_close": quote.price - quote.change if quote.change else quote.price,
                "change": round(quote.change, 2),
                "change_pct": round(quote.change_pct, 2),
                "market_cap": 0.0,
                "week_52_high": quote.price,
                "week_52_low": quote.price,
                "source": "upstox",
                "timestamp": quote.timestamp.isoformat() if quote.timestamp else datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.debug(f"Upstox quote failed for {symbol}: {e}")
            return None

    @classmethod
    async def _upstox_history(cls, symbol: str, interval: str, period: str) -> list[dict] | None:
        """Try Upstox for historical bars. Returns None if unavailable."""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            if not getattr(settings, "UPSTOX_ENABLED", False) or not getattr(settings, "UPSTOX_ANALYTICS_TOKEN", None):
                return None
            from app.services.ingestion.upstox_source import UpstoxSource
            source = UpstoxSource()
            period_days = {"1d": 30, "5d": 150, "1w": 180, "1mo": 730, "1y": 365, "2y": 730}
            days = period_days.get(period, 30)
            if period.endswith('d') and period[:-1].isdigit():
                days = int(period[:-1])
            elif period.endswith('y') and period[:-1].isdigit():
                days = int(period[:-1]) * 365
            start = datetime.now(UTC) - timedelta(days=days)
            end = datetime.now(UTC)
            bars = await source.get_ohlcv(symbol, interval, start, end)
            if not bars:
                return None
            return [
                {
                    "time": b.time.isoformat(),
                    "timestamp": b.time.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                    "source": "upstox",
                }
                for b in bars
            ]
        except Exception as e:
            logger.debug(f"Upstox history failed for {symbol}: {e}")
            return None

    @staticmethod
    async def get_quote(symbol: str) -> dict:
        """Fetch live quote — tries DB → Upstox → yfinance."""
        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import Instrument, QuoteSnapshot

        sym = MarketDataService._normalize_symbol(symbol)

        try:
            async with async_session_factory() as db:
                result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == sym))
                instrument = result.scalars().first()
                if instrument:
                    result = await db.execute(
                        select(QuoteSnapshot)
                        .where(QuoteSnapshot.instrument_id == instrument.id)
                        .order_by(QuoteSnapshot.observed_at.desc())
                        .limit(1)
                    )
                    quote = result.scalars().first()
                    if quote and safe_float(quote.price) > 0:
                        return {
                            "symbol": sym,
                            "price": float(quote.price),
                            "open": float(quote.price),
                            "high": float(quote.price),
                            "low": float(quote.price),
                            "volume": int(quote.volume or 0),
                            "previous_close": float(quote.price),
                            "change": float(quote.change or 0.0),
                            "change_pct": float(quote.change_pct or 0.0),
                            "market_cap": 0.0,
                            "week_52_high": float(quote.price),
                            "week_52_low": float(quote.price),
                            "source": "canonical_db",
                            "timestamp": quote.observed_at.isoformat(),
                        }
        except Exception as db_err:
            logger.debug(f"DB quote lookup failed for {sym}: {db_err}")

        upstox_result = await MarketDataService._upstox_quote(symbol)
        if upstox_result:
            return upstox_result

        return await MarketDataService._yfinance_quote(symbol)

    @classmethod
    async def _yfinance_history(cls, symbol: str, interval: str, period: str) -> list[dict]:
        """Fetch historical bars directly from yfinance."""
        sym = cls._normalize_symbol(symbol)
        yf_sym = sym if sym.startswith("^") or "." in sym else f"{sym}.NS"

        await cls._throttle_yfinance(yf_sym)

        def _fetch():
            session = cls.get_session()
            df = yf.download(
                yf_sym, period=period, interval=interval,
                progress=False, threads=False, session=session,
            )
            if df.empty:
                return []
            bars = []
            for ts, row in df.iterrows():
                bars.append({
                    "time": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    "open": safe_float(row.get("Open")),
                    "high": safe_float(row.get("High")),
                    "low": safe_float(row.get("Low")),
                    "close": safe_float(row.get("Close")),
                    "volume": safe_float(row.get("Volume")),
                })
            return bars

        async with cls._semaphore:
            bars = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=15.0)
            return HistoryList(bars, source="yfinance")

    @staticmethod
    async def fetch_live_yfinance_quote(symbol: str) -> dict:
        """Fetch a live quote directly from yfinance (no DB involved)."""
        sym = MarketDataService._normalize_symbol(symbol)
        await MarketDataService._throttle_yfinance(sym)
        session = MarketDataService.get_session()
        loop = asyncio.get_event_loop()

        def _sync_fetch():
            ticker = yf.Ticker(sym, session=session)
            info = ticker.info or {}
            fast = ticker.fast_info or {}
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or getattr(fast, "last_price", None)
                or 0.0
            )
            prev_close = (
                info.get("previousClose")
                or info.get("regularMarketPreviousClose")
                or getattr(fast, "previous_close", None)
                or price
            )
            change = float(price) - float(prev_close) if prev_close else 0.0
            change_pct = (change / float(prev_close) * 100.0) if prev_close else 0.0
            volume = (
                info.get("volume")
                or info.get("regularMarketVolume")
                or getattr(fast, "three_month_average_volume", None)
                or 0
            )
            return {
                "price": float(price),
                "change": round(change, 4),
                "change_pct": round(change_pct, 4),
                "volume": int(volume or 0),
                "name": info.get("shortName") or info.get("longName") or sym,
                "source": "yfinance",
            }

        return await loop.run_in_executor(None, _sync_fetch)

    @staticmethod
    async def get_history(symbol: str, interval: str, period: str) -> list[dict]:
        """Fetch historical bars — tries canonical DB first, falls back to yfinance."""
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import OHLCV, Instrument

        sym = MarketDataService._normalize_symbol(symbol)

        period_days = {"1m": 1, "5m": 5, "15m": 5, "1h": 30, "1d": 30, "5d": 150, "1wk": 180, "1w": 180, "1mo": 730, "3mo": 1825, "6mo": 3650, "1y": 365, "2y": 730, "5y": 1825, "max": 3650}

        days = period_days.get(period, 30)
        if period.endswith('d') and period[:-1].isdigit():
            days = int(period[:-1])
        elif period.endswith('y') and period[:-1].isdigit():
            days = int(period[:-1]) * 365

        start_time = datetime.now(UTC) - timedelta(days=days)

        try:
            async with async_session_factory() as db:
                result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == sym))
                instrument = result.scalars().first()
                if instrument:
                    result = await db.execute(
                        select(OHLCV)
                        .where(
                            (OHLCV.instrument_id == instrument.id) &
                            (OHLCV.interval == interval) &
                            (OHLCV.timestamp >= start_time)
                        )
                        .order_by(OHLCV.timestamp.asc())
                    )
                    bars_data = result.scalars().all()

                    if bars_data:
                        bars = []
                        for b in bars_data:
                            bars.append({
                                "time": b.timestamp.isoformat(),
                                "timestamp": b.timestamp.isoformat(),
                                "open": float(b.open),
                                "high": float(b.high),
                                "low": float(b.low),
                                "close": float(b.close),
                                "volume": float(b.volume),
                            })
                        return HistoryList(bars, source="canonical_db")
        except Exception as db_err:
            logger.debug(f"DB history lookup failed for {sym}: {db_err}")

        upstox_bars = await MarketDataService._upstox_history(symbol, interval, period)
        if upstox_bars:
            return upstox_bars

        return await MarketDataService._yfinance_history(symbol, interval, period)

    @classmethod
    async def get_intraday_candles(cls, symbol: str, interval: str) -> list[dict]:
        """Fetch intraday candles for a symbol, mapping interval to a sensible period.

        Falls back to empty or NSE fallback if yfinance fails.
        """
        period_map = {"1m": "5d", "5m": "30d", "15m": "30d", "1h": "60d", "1d": "1y"}
        period = period_map.get(interval, "30d")

        try:
            bars = await cls.get_history(symbol, interval=interval, period=period)
            if bars:
                return bars
        except Exception as e:
            logger.warning(
                f"Failed to fetch intraday candles for {symbol} ({interval}) via yfinance: {e}"
            )

        # If empty or fails, attempt a fallback. If it is an NSE symbol, we can try to append a live quote as a single candle
        try:
            logger.info(f"Falling back to NSE service/quote for {symbol}")
            q = await cls.get_quote(symbol)
            if q and q.get("price") is not None:
                return [
                    {
                        "time": datetime.now(UTC).isoformat(),
                        "open": q["price"],
                        "high": q["price"],
                        "low": q["price"],
                        "close": q["price"],
                        "volume": q.get("volume", 0.0),
                    }
                ]
        except Exception as fe:
            logger.warning(f"NSE fallback/quote fetch also failed for {symbol}: {fe}")

        return []

    # get_movers/get_nifty50_movers/_fetch_movers_sync were removed: they were
    # dead code (zero production callers), referenced the deprecated hardcoded
    # NSE_NIFTY50_DEPRECATED universe, and _fetch_movers_sync called
    # yf.download directly from a business-service method rather than through
    # ingestion, violating the DB-first architecture. GET /api/v1/market/movers
    # (app/api/v1/market.py) is the canonical, DB-first replacement.

    @staticmethod
    async def get_indices() -> list[dict]:
        """Fetch quotes for all major NSE/BSE indices concurrently."""
        index_pairs = MarketDataService.NSE_INDICES
        index_symbols = [sym for sym, _ in index_pairs]
        names_map = {sym: name for sym, name in index_pairs}

        tasks = [MarketDataService.get_quote(sym) for sym in index_symbols]
        res = await asyncio.gather(*tasks, return_exceptions=True)

        indices = []
        for sym, q in zip(index_symbols, res, strict=False):
            if isinstance(q, Exception):
                logger.debug(f"Index quote failed for symbol={sym}: {q}")
                continue
            if not q or q.get("price") is None:
                continue
            indices.append(
                {
                    "name": names_map.get(sym, sym),
                    "ticker": sym,
                    "value": q["price"],
                    "change": q["change"],
                    "change_pct": q["change_pct"],
                }
            )
        return indices

    @staticmethod
    async def get_ticker_info(symbol: str) -> dict:
        """Fetch general info for symbol (PE, Market Cap, etc.)."""
        sym = MarketDataService._normalize_symbol(symbol)

        def _fetch_info():
            session = MarketDataService.get_session()
            ticker = yf.Ticker(sym, session=session)
            try:
                info = ticker.info or {}
                return {
                    "trailingPE": info.get("trailingPE"),
                    "forwardPE": info.get("forwardPE"),
                    "marketCap": info.get("marketCap"),
                    "shortName": info.get("shortName"),
                }
            except Exception:
                return {}

        async with MarketDataService._semaphore:
            return await asyncio.to_thread(_fetch_info)

    @staticmethod
    async def get_ticker_history_df(symbol: str, period: str, interval: str):
        """Fetch history dataframe directly from yfinance Ticker."""
        sym = MarketDataService._normalize_symbol(symbol)

        # Check in-memory cache
        cache_key = f"mds:df:{sym}:{interval}:{period}"
        now = datetime.now(UTC).timestamp()
        if cache_key in MarketDataService._in_memory_ticker_history_df_cache:
            cached, ts = MarketDataService._in_memory_ticker_history_df_cache[cache_key]
            if now - ts < 300:
                return cached

        def _fetch():
            session = MarketDataService.get_session()
            ticker = yf.Ticker(sym, session=session)
            return ticker.history(period=period, interval=interval)

        async with MarketDataService._semaphore:
            result = await asyncio.to_thread(_fetch)

        if not result.empty:
            MarketDataService._in_memory_ticker_history_df_cache[cache_key] = (result, now)
            return result

    @staticmethod
    async def download_raw(
        tickers: str,
        start: datetime | str,
        end: datetime | str,
        interval: str,
        auto_adjust: bool = False,
        progress: bool = False,
        threads: bool = False,
    ):
        """Wrapper for yfinance.download to allow ingestion pipeline usage."""

        def _download():
            session = MarketDataService.get_session()
            return yf.download(
                tickers=tickers,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=progress,
                threads=threads,
                session=session,
            )

        async with MarketDataService._semaphore:
            return await asyncio.to_thread(_download)

    @staticmethod
    async def get_live_quote(symbol: str) -> dict:
        """Fetch live quote using yfinance — 100% free with throttling and fallback."""
        sym = MarketDataService._normalize_symbol(symbol)
        try:
            await MarketDataService._throttle_yfinance(sym)
            quote = await MarketDataService.get_quote(sym)
            if quote:
                return quote
        except Exception as e:
            logger.warning(f"get_live_quote: yfinance failed for {sym}: {e}. Trying cache...")

        # Fallback to cached
        cache_key = f"mds:quote:{sym}"
        try:
            from app.database.redis_client import get_redis_client

            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        # If cache fails too, raise a 503 since we have no real data
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "code": "MARKET_DATA_UNAVAILABLE",
                "message": f"Live quote unavailable for {sym}",
            },
        )

    @staticmethod
    async def get_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> list:
        """
        period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval options: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        Note: 1m data only available for last 7 days
              5m data only available for last 60 days
        """
        sym = MarketDataService._normalize_symbol(symbol)
        try:
            await MarketDataService._throttle_yfinance(sym)
            loop = asyncio.get_event_loop()
            bars = await loop.run_in_executor(
                None, MarketDataService._fetch_ohlcv_sync, sym, period, interval
            )
            if bars:
                return bars
        except Exception as e:
            logger.warning(f"get_ohlcv: yfinance failed for {sym}: {e}. Trying history fallback...")

        # Fallback to get_history and map it
        try:
            bars_iso = await MarketDataService.get_history(sym, interval, period)
            if bars_iso:
                import pandas as pd

                mapped_bars = []
                for b in bars_iso:
                    unix_ts = int(pd.Timestamp(b["time"]).timestamp())
                    mapped_bars.append(
                        {
                            "time": unix_ts,
                            "open": float(b["open"]),
                            "high": float(b["high"]),
                            "low": float(b["low"]),
                            "close": float(b["close"]),
                            "volume": int(b["volume"]),
                        }
                    )
                return mapped_bars
        except Exception as ex:
            logger.error(f"get_ohlcv: history fallback failed for {sym}: {ex}")

        return []

    @staticmethod
    def _fetch_ohlcv_sync(symbol: str, period: str, interval: str) -> list:
        import pandas as pd

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return []
        df.reset_index(inplace=True)

        bars = []
        for _, row in df.iterrows():
            ts = row["Datetime"] if "Datetime" in row else row["Date"]
            if hasattr(ts, "timestamp"):
                unix_ts = int(ts.timestamp())
            else:
                unix_ts = int(pd.Timestamp(ts).timestamp())

            bars.append(
                {
                    "time": unix_ts,
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
            )
        return bars

