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


class MarketDataService:
    # Class-level session and caches for sockets, rate-limiting, and performance optimization
    _session = None
    _in_memory_quote_cache = {}  # key -> (quote_dict, timestamp)
    _in_memory_history_cache = {}  # key -> (history_list, timestamp)
    _in_memory_ticker_history_df_cache = {}  # key -> (df, timestamp)
    _semaphore = asyncio.Semaphore(8)  # limit concurrency to avoid descriptor exhaustion under select()
    
    _last_yfinance_request_time = 0.0
    _last_nse_request_time = 0.0

    @classmethod
    async def _throttle_yfinance(cls, symbol: str) -> None:
        now = asyncio.get_event_loop().time()
        elapsed = now - cls._last_yfinance_request_time
        if elapsed < 0.25:  # ensure at least 250ms gap between any yfinance calls
            await asyncio.sleep(0.25 - elapsed)
        cls._last_yfinance_request_time = asyncio.get_event_loop().time()

    @classmethod
    async def _throttle_nse(cls) -> None:
        now = asyncio.get_event_loop().time()
        elapsed = now - cls._last_nse_request_time
        if elapsed < 0.2:  # max 5 requests per second
            await asyncio.sleep(0.2 - elapsed)
        cls._last_nse_request_time = asyncio.get_event_loop().time()

    # NSE Top 50 stocks with .NS suffix
    NSE_NIFTY50 = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
        "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
        "AXISBANK.NS","LT.NS","WIPRO.NS","HCLTECH.NS","ASIANPAINT.NS",
        "MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","BAJFINANCE.NS",
        "NESTLEIND.NS","TATAMOTORS.NS","TATASTEEL.NS","NTPC.NS","POWERGRID.NS",
        "ONGC.NS","COALINDIA.NS","JSWSTEEL.NS","GRASIM.NS","ADANIENT.NS",
        "ADANIPORTS.NS","BAJAJFINSV.NS","TECHM.NS","DRREDDY.NS","CIPLA.NS",
        "DIVISLAB.NS","BRITANNIA.NS","APOLLOHOSP.NS","TATACONSUM.NS","HEROMOTOCO.NS",
        "EICHERMOT.NS","BPCL.NS","SHREECEM.NS","INDUSINDBK.NS","UPL.NS",
        "HINDALCO.NS","SBILIFE.NS","HDFCLIFE.NS","M&M.NS","BAJAJ-AUTO.NS"
    ]

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
                # Add source field
                up_quote["source"] = "NSE"
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
                "source": "yfinance",
            }

        try:
            await MarketDataService._throttle_yfinance(sym)
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
                if isinstance(cached, dict) and "bars" in cached:
                    return HistoryList(cached["bars"], source=cached.get("source", "yfinance"))
                return cached

        redis = None
        try:
            from app.database.redis_client import get_redis_client
            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                if isinstance(cached_data, dict) and cached_data.get("error"):
                    MarketDataService._in_memory_history_cache[cache_key] = (cached_data, now)
                    return []
                if isinstance(cached_data, dict) and "bars" in cached_data:
                    res_list = HistoryList(cached_data["bars"], source=cached_data.get("source", "yfinance"))
                else:
                    res_list = HistoryList(cached_data, source="yfinance")
                MarketDataService._in_memory_history_cache[cache_key] = (cached_data, now)
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

        result = None
        try:
            from app.services.data_ingestion.orchestrator import DataIngestionOrchestrator, IngestionTask
            from datetime import timedelta
            
            orch_interval_map = {
                "1m": "1m",
                "3m": "5m",
                "5m": "5m",
                "10m": "15m",
                "15m": "15m",
                "30m": "15m",
                "45m": "1h",
                "1h": "1h",
                "2h": "1h",
                "4h": "1d",
                "1d": "1d",
                "1D": "1d",
                "1w": "1d",
                "1W": "1d",
                "1mo": "1d",
                "1M": "1d"
            }
            orch_interval = orch_interval_map.get(interval, "1d")
            
            period_days = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825,
                "max": 3650,
            }
            days = period_days.get(period, 30)
            start_time = datetime.now(UTC) - timedelta(days=days)
            end_time = datetime.now(UTC)
            
            asset_type = "CRYPTO" if sym.endswith("-USD") else "EQUITY"
            task = IngestionTask(
                symbol=sym,
                interval=orch_interval,
                start=start_time,
                end=end_time,
                asset_type=asset_type
            )
            orchestrator = DataIngestionOrchestrator(max_concurrency=4)
            source_name, ohlcv_bars = await orchestrator.fetch_task(task)
            if ohlcv_bars:
                bars_list = []
                for b in ohlcv_bars:
                    time_str = b.time.isoformat() if hasattr(b.time, "isoformat") else str(b.time)
                    bars_list.append({
                        "time": time_str,
                        "open": float(b.open),
                        "high": float(b.high),
                        "low": float(b.low),
                        "close": float(b.close),
                        "volume": float(b.volume),
                    })
                result = HistoryList(bars_list, source=source_name)
        except Exception as e:
            logger.info(f"Orchestrator fetch failed for {sym}: {e}, falling back to direct yfinance...")

        if not result:
            try:
                async with MarketDataService._semaphore:
                    raw_bars = await asyncio.to_thread(_fetch_history)
                if raw_bars:
                    result = HistoryList(raw_bars, source="yfinance")
            except Exception as e:
                logger.warning(f"yfinance download failed for {sym}: {e}")
                result = None

        now_ts = datetime.now(UTC).timestamp()
        if not result:
            failure_dict = {"error": True}
            MarketDataService._in_memory_history_cache[cache_key] = (failure_dict, now_ts)
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(failure_dict))
                except Exception:
                    pass
        else:
            cache_payload = {
                "source": result.source,
                "bars": list(result)
            }
            MarketDataService._in_memory_history_cache[cache_key] = (cache_payload, now_ts)
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(cache_payload))
                except Exception as se:
                    logger.warning(f"Redis cache set failed for get_history key={cache_key}: {se}")

        return result

    @classmethod
    async def get_intraday_candles(cls, symbol: str, interval: str) -> list[dict]:
        """Fetch intraday candles for a symbol, mapping interval to a sensible period.
        
        Falls back to empty or NSE fallback if yfinance fails.
        """
        period_map = {
            "1m": "5d",
            "5m": "30d",
            "15m": "30d",
            "1h": "60d",
            "1d": "1y"
        }
        period = period_map.get(interval, "30d")
        
        try:
            bars = await cls.get_history(symbol, interval=interval, period=period)
            if bars:
                return bars
        except Exception as e:
            logger.warning(f"Failed to fetch intraday candles for {symbol} ({interval}) via yfinance: {e}")
            
        # If empty or fails, attempt a fallback. If it is an NSE symbol, we can try to append a live quote as a single candle
        try:
            logger.info(f"Falling back to NSE service/quote for {symbol}")
            q = await cls.get_quote(symbol)
            if q and q.get("price") is not None:
                return [{
                    "time": datetime.now(UTC).isoformat(),
                    "open": q["price"],
                    "high": q["price"],
                    "low": q["price"],
                    "close": q["price"],
                    "volume": q.get("volume", 0.0),
                }]
        except Exception as fe:
            logger.warning(f"NSE fallback/quote fetch also failed for {symbol}: {fe}")
            
        return []

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

        # If cache fails too, construct a minimal fallback dict using database or defaults
        return {
            "symbol": sym,
            "price": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": 0,
            "timestamp": datetime.utcnow().isoformat()
        }

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
            bars = await loop.run_in_executor(None, MarketDataService._fetch_ohlcv_sync, sym, period, interval)
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
                    mapped_bars.append({
                        "time": unix_ts,
                        "open": float(b["open"]),
                        "high": float(b["high"]),
                        "low": float(b["low"]),
                        "close": float(b["close"]),
                        "volume": int(b["volume"])
                    })
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
            
            bars.append({
                "time": unix_ts,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"])
            })
        return bars

    @staticmethod
    async def get_nifty50_movers() -> dict:
        """Get top gainers and losers from Nifty 50 — free via yfinance batch."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, MarketDataService._fetch_movers_sync)

    @staticmethod
    def _fetch_movers_sync() -> dict:
        # Batch download is faster than individual calls
        data = yf.download(
            MarketDataService.NSE_NIFTY50[:20],  # Limit for free tier speed
            period="2d", interval="1d", group_by="ticker", progress=False
        )
        movers = []
        for sym in MarketDataService.NSE_NIFTY50[:20]:
            try:
                sym_data = data[sym] if sym in data.columns.get_level_values(0) else None
                if sym_data is not None and len(sym_data) >= 2:
                    today = float(sym_data["Close"].iloc[-1])
                    yesterday = float(sym_data["Close"].iloc[-2])
                    chg_pct = ((today - yesterday) / yesterday) * 100
                    movers.append({"symbol": sym.replace(".NS",""), "price": today, "change_pct": round(chg_pct, 2)})
            except Exception:
                continue
        
        movers_sorted = sorted(movers, key=lambda x: x["change_pct"], reverse=True)
        return {
            "gainers": movers_sorted[:5],
            "losers": movers_sorted[-5:][::-1]
        }
