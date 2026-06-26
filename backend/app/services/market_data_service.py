# backend/app/services/market_data_service.py
"""Market Data Service — Single point of contact for all yfinance data."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime
import yfinance as yf

from app.core.logging import get_logger

logger = get_logger(__name__)


def safe_float(val, fallback=0.0) -> float:
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return fallback
        return f
    except Exception:
        return fallback


class MarketDataService:
    # Class-level session and caches for sockets, rate-limiting, and performance optimization
    _session = None
    _in_memory_quote_cache = {}  # key -> (quote_dict, timestamp)
    _in_memory_history_cache = {}  # key -> (history_list, timestamp)
    _in_memory_ticker_history_df_cache = {}  # key -> (df, timestamp)
    _semaphore = asyncio.Semaphore(8)  # limit concurrency to avoid descriptor exhaustion under select()

    @classmethod
    def get_session(cls):
        if cls._session is None:
            import requests
            cls._session = requests.Session()
            cls._session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
        return cls._session

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Automatically appends .NS if the symbol has no dot, caret, or dash.
        
        Also maps index symbols like NIFTY50, BANKNIFTY, SENSEX to their Yahoo Finance tickers.
        """
        s = symbol.upper().strip()
        
        # Map indices to their correct yfinance tickers
        mappings = {
            "NIFTY50": "^NSEI",
            "NIFTY 50": "^NSEI",
            "NIFTY_50": "^NSEI",
            "NIFTY50.NS": "^NSEI",
            "NIFTY_50.NS": "^NSEI",
            "NIFTY 50.NS": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "BANK NIFTY": "^NSEBANK",
            "BANK_NIFTY": "^NSEBANK",
            "BANKNIFTY.NS": "^NSEBANK",
            "BANK_NIFTY.NS": "^NSEBANK",
            "BANK NIFTY.NS": "^NSEBANK",
            "NSEBANK": "^NSEBANK",
            "NSEBANK.NS": "^NSEBANK",
            "SENSEX": "^BSESN",
            "SENSEX.NS": "^BSESN",
        }
        if s in mappings:
            return mappings[s]
            
        # Bypass common US stock tickers to prevent appending .NS
        us_tickers = {
            "AAPL", "MSFT", "GOOG", "GOOGL", "TSLA", "AMZN", "NVDA", "META", 
            "NFLX", "AMD", "INTC", "QCOM", "AVGO", "CSCO", "PEP", "KO", "DIS"
        }
        if s in us_tickers:
            return s
            
        if "." not in s and "^" not in s and "-" not in s:
            return f"{s}.NS"
        return s

    @staticmethod
    async def get_quote(symbol: str) -> dict:
        """Fetch live quote using yfinance Ticker.
        
        Uses fast_info for live price, falls back to history closes if unavailable.
        Raises ValueError with the symbol name if result is empty.
        Caches in in-memory and Redis.
        """
        sym = MarketDataService._normalize_symbol(symbol)
        
        # 1. Check Upstox live cache first
        try:
            from app.services.upstox_service import UpstoxService
            up_quote = UpstoxService.get_cached_quote(sym)
            if up_quote:
                return up_quote
        except Exception as ue:
            logger.debug(f"Upstox live cache check failed for {sym}: {ue}")
            
        cache_key = f"mds:quote:{sym}"
        now = datetime.now(UTC).timestamp()
        
        # Check fast in-memory cache first
        if cache_key in MarketDataService._in_memory_quote_cache:
            cached, ts = MarketDataService._in_memory_quote_cache[cache_key]
            if isinstance(cached, dict) and cached.get("error"):
                if now - ts < 60:  # Cache failures for 60 seconds
                    raise ValueError(sym)
            elif now - ts < 20:
                return cached

        redis = None
        try:
            from app.database.redis_client import get_redis_client
            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                res_dict = json.loads(cached)
                if isinstance(res_dict, dict) and res_dict.get("error"):
                    MarketDataService._in_memory_quote_cache[cache_key] = (res_dict, now)
                    raise ValueError(sym)
                MarketDataService._in_memory_quote_cache[cache_key] = (res_dict, now)
                return res_dict
        except Exception as re:
            logger.warning(f"Redis cache check failed for get_quote key={cache_key}: {re}")

        def _fetch_quote() -> dict:
            session = MarketDataService.get_session()
            ticker = yf.Ticker(sym, session=session)
            
            try:
                info = ticker.fast_info
                price = getattr(info, "last_price", None)
            except Exception:
                info = None
                price = None

            # Fallback to history close if last_price is missing or invalid
            if price is None or math.isnan(price) or price <= 0:
                try:
                    hist = ticker.history(period="5d", interval="1d")
                except Exception as he:
                    logger.warning(f"yfinance history fetch failed for {sym}: {he}")
                    raise ValueError(sym) from he
                if hist.empty:
                    raise ValueError(sym)
                price = float(hist.iloc[-1]["Close"])
                prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else price
                open_p = float(hist.iloc[-1]["Open"])
                high = float(hist.iloc[-1]["High"])
                low = float(hist.iloc[-1]["Low"])
                volume = int(hist.iloc[-1]["Volume"])
                market_cap = 0.0
                week_52_high = high
                week_52_low = low
            else:
                try:
                    hist = ticker.history(period="5d", interval="1d")
                except Exception as he:
                    logger.warning(f"yfinance history fetch failed for {sym}: {he}")
                    raise ValueError(sym) from he
                if hist.empty:
                    raise ValueError(sym)
                prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else price
                open_p = float(hist.iloc[-1]["Open"]) if not hist.empty else price
                high = float(hist.iloc[-1]["High"]) if not hist.empty else price
                low = float(hist.iloc[-1]["Low"]) if not hist.empty else price
                volume = int(hist.iloc[-1]["Volume"]) if not hist.empty else 0
                
                try:
                    info_dict = ticker.info or {}
                    market_cap = float(info_dict.get("marketCap") or 0.0)
                    week_52_high = float(info_dict.get("fiftyTwoWeekHigh") or getattr(info, "year_high", high))
                    week_52_low = float(info_dict.get("fiftyTwoWeekLow") or getattr(info, "year_low", low))
                except Exception:
                    market_cap = 0.0
                    week_52_high = getattr(info, "year_high", high)
                    week_52_low = getattr(info, "year_low", low)

            change = price - prev_close
            change_pct = (change / prev_close * 100.0) if prev_close != 0.0 else 0.0

            return {
                "symbol": sym,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 4),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volume": int(volume),
                "previous_close": round(prev_close, 2),
                "market_cap": market_cap,
                "week_52_high": round(week_52_high, 2) if week_52_high else None,
                "week_52_low": round(week_52_low, 2) if week_52_low else None,
            }

        try:
            async with MarketDataService._semaphore:
                result = await asyncio.to_thread(_fetch_quote)
            if not result or result.get("price") is None:
                raise ValueError(sym)
        except Exception as e:
            # Tombstone / cache the failure so we don't spam network
            now_ts = datetime.now(UTC).timestamp()
            failure_dict = {"error": True, "message": str(e)}
            MarketDataService._in_memory_quote_cache[cache_key] = (failure_dict, now_ts)
            if redis:
                try:
                    await redis.setex(cache_key, 60, json.dumps(failure_dict))
                except Exception:
                    pass
            if isinstance(e, ValueError):
                raise
            raise ValueError(sym) from e

        # Store in caches
        now_ts = datetime.now(UTC).timestamp()
        MarketDataService._in_memory_quote_cache[cache_key] = (result, now_ts)
        if redis:
            try:
                await redis.setex(cache_key, 20, json.dumps(result))
            except Exception as se:
                logger.warning(f"Redis cache set failed for get_quote key={cache_key}: {se}")

        return result

    @staticmethod
    async def get_history(symbol: str, interval: str, period: str) -> list[dict]:
        """Fetch historical bars using yfinance download.
        
        Maps frontend timeframes to yfinance interval strings.
        """
        sym = MarketDataService._normalize_symbol(symbol)
        
        tf_map = {
            "1m": "1m",
            "3m": "5m",
            "5m": "5m",
            "10m": "15m",
            "15m": "15m",
            "30m": "30m",
            "45m": "60m",
            "1h": "60m",
            "2h": "60m",
            "4h": "1d",
            "1d": "1d",
            "1D": "1d",
            "1w": "1wk",
            "1W": "1wk",
            "1mo": "1mo",
            "1M": "1mo"
        }
        yf_interval = tf_map.get(interval, "1d")
        
        cache_key = f"mds:history:{sym}:{yf_interval}:{period}"
        now = datetime.now(UTC).timestamp()

        # Check in-memory cache
        if cache_key in MarketDataService._in_memory_history_cache:
            cached, ts = MarketDataService._in_memory_history_cache[cache_key]
            if now - ts < 300:
                if isinstance(cached, dict) and cached.get("error"):
                    return []
                return cached

        redis = None
        try:
            from app.database.redis_client import get_redis_client
            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                res_list = json.loads(cached)
                if isinstance(res_list, dict) and res_list.get("error"):
                    MarketDataService._in_memory_history_cache[cache_key] = (res_list, now)
                    return []
                MarketDataService._in_memory_history_cache[cache_key] = (res_list, now)
                return res_list
        except Exception as re:
            logger.warning(f"Redis cache check failed for get_history key={cache_key}: {re}")

        def _fetch_history() -> list[dict]:
            import pandas as pd
            session = MarketDataService.get_session()
            try:
                df = yf.download(sym, period=period, interval=yf_interval, auto_adjust=True, progress=False, threads=False, session=session)
            except Exception as de:
                logger.warning(f"yfinance download exception for {sym}: {de}")
                return []
            if df.empty:
                return []
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            col = "Datetime" if "Datetime" in df.columns else "Date"
            bars = []
            for _, row in df.iterrows():
                val = row[col]
                if hasattr(val, "isoformat"):
                    time_str = val.isoformat()
                else:
                    time_str = str(val)
                bars.append({
                    "time": time_str,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row.get("Volume", 0.0) or 0.0),
                })
            return bars

        try:
            async with MarketDataService._semaphore:
                result = await asyncio.to_thread(_fetch_history)
        except Exception as e:
            logger.warning(f"yfinance download failed for {sym}: {e}")
            result = []

        now_ts = datetime.now(UTC).timestamp()
        if not result:
            # Tombstone history failures for 5 minutes
            failure_dict = {"error": True}
            MarketDataService._in_memory_history_cache[cache_key] = (failure_dict, now_ts)
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(failure_dict))
                except Exception:
                    pass
        else:
            MarketDataService._in_memory_history_cache[cache_key] = (result, now_ts)
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(result))
                except Exception as se:
                    logger.warning(f"Redis cache set failed for get_history key={cache_key}: {se}")

        return result

    @staticmethod
    async def get_movers(n: int = 10, mover_type: str = "gainers") -> list[dict]:
        """Fetch quotes concurrently for 30 hardcoded NIFTY 50 symbol roots.
        
        Sorts by change_pct and returns top n.
        """
        symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "BHARTIARTL", "SBIN", "ITC", "LT", "HINDUNILVR",
            "AXISBANK", "KOTAKBANK", "ADANIENT", "ULTRACEMCO", "BAJFINANCE",
            "MARUTI", "SUNPHARMA", "NTPC", "TATASTEEL", "POWERGRID",
            "ADANIPORTS", "TITAN", "COALINDIA", "WIPRO", "HCLTECH",
            "ONGC", "JSWSTEEL", "ASIANPAINT", "NESTLEIND", "GRASIM"
        ]
        
        tasks = [MarketDataService.get_quote(sym) for sym in symbols]
        quotes_res = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = []
        for sym, q in zip(symbols, quotes_res):
            if isinstance(q, Exception):
                logger.debug(f"Mover quote failed for symbol={sym}: {q}")
                continue
            if not q or q.get("price") is None:
                continue
            quotes.append(q)

        if not quotes:
            return []

        if mover_type == "gainers":
            quotes.sort(key=lambda x: x["change_pct"], reverse=True)
        elif mover_type == "losers":
            quotes.sort(key=lambda x: x["change_pct"])
        elif mover_type == "volume":
            quotes.sort(key=lambda x: x["volume"], reverse=True)
        else:  # momentum
            quotes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

        movers = []
        for i, q in enumerate(quotes[:n]):
            movers.append({
                "ticker": q["symbol"],
                "name": q["symbol"].split(".")[0],
                "price": q["price"],
                "change_pct": q["change_pct"],
                "volume": q["volume"],
                "rank": i + 1,
            })
        return movers

    @staticmethod
    async def get_indices() -> list[dict]:
        """Fetch quotes for ^NSEI, ^BSESN, and ^NSEBANK concurrently.
        
        Maps ticker symbols to display names: NIFTY 50, BSE Sensex, Bank Nifty.
        """
        index_symbols = ["^NSEI", "^BSESN", "^NSEBANK"]
        tasks = [MarketDataService.get_quote(sym) for sym in index_symbols]
        res = await asyncio.gather(*tasks, return_exceptions=True)
        
        names_map = {
            "^NSEI": "NIFTY 50",
            "^BSESN": "BSE Sensex",
            "^NSEBANK": "Bank Nifty"
        }
        
        indices = []
        for sym, q in zip(index_symbols, res):
            if isinstance(q, Exception):
                logger.debug(f"Index quote failed for symbol={sym}: {q}")
                continue
            if not q or q.get("price") is None:
                continue
            indices.append({
                "name": names_map.get(sym, sym),
                "ticker": sym,
                "value": q["price"],
                "change": q["change"],
                "change_pct": q["change_pct"]
            })
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
            MarketDataService._in_memory_ticker_history_df_cache[cache_key] = (result, datetime.now(UTC).timestamp())
        return result

    @staticmethod
    async def download_raw(tickers: str, start: datetime | str, end: datetime | str, interval: str, auto_adjust: bool = False, progress: bool = False, threads: bool = False):
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
                session=session
            )
        async with MarketDataService._semaphore:
            return await asyncio.to_thread(_download)
