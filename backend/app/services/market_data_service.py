# backend/app/services/market_data_service.py
"""Market Data Service — Single point of contact for all yfinance data."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime

import yfinance as yf

from app.core.logging import get_logger
from app.services.indian_stock_api import IndianStockAPI

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
    _semaphore = asyncio.Semaphore(
        8
    )  # limit concurrency to avoid descriptor exhaustion under select()

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
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "HINDUNILVR.NS",
        "ITC.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "LT.NS",
        "WIPRO.NS",
        "HCLTECH.NS",
        "ASIANPAINT.NS",
        "MARUTI.NS",
        "SUNPHARMA.NS",
        "TITAN.NS",
        "ULTRACEMCO.NS",
        "BAJFINANCE.NS",
        "NESTLEIND.NS",
        "M&M.NS",
        "TATASTEEL.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "ONGC.NS",
        "COALINDIA.NS",
        "JSWSTEEL.NS",
        "GRASIM.NS",
        "ADANIENT.NS",
        "ADANIPORTS.NS",
        "BAJAJFINSV.NS",
        "TECHM.NS",
        "DRREDDY.NS",
        "CIPLA.NS",
        "DIVISLAB.NS",
        "BRITANNIA.NS",
        "APOLLOHOSP.NS",
        "TATACONSUM.NS",
        "HEROMOTOCO.NS",
        "EICHERMOT.NS",
        "BPCL.NS",
        "SHREECEM.NS",
        "INDUSINDBK.NS",
        "UPL.NS",
        "HINDALCO.NS",
        "SBILIFE.NS",
        "HDFCLIFE.NS",
        "TATAMOTORS.NS",
        "BAJAJ-AUTO.NS",
    ]

    @classmethod
    def get_session(cls):
        if cls._session is None:
            import requests

            cls._session = requests.Session()
            cls._session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
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

        if "." not in s and "^" not in s and "-" not in s:
            return f"{s}.NS"
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
        datetime.now(UTC).timestamp()

        redis = None
        try:
            from app.database.redis_client import get_redis_client

            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                res_dict = json.loads(cached)
                if isinstance(res_dict, dict) and res_dict.get("error"):
                    raise ValueError(sym)
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

            if price is None or math.isnan(price) or price <= 0:
                price = None
                open_p = None
                high = None
                low = None
                volume = None
                prev_close = None
            else:
                try:
                    info_dict = ticker.info or {}
                    market_cap = float(info_dict.get("marketCap") or 0.0)
                    week_52_high = float(
                        info_dict.get("fiftyTwoWeekHigh") or getattr(info, "year_high", price)
                    )
                    week_52_low = float(
                        info_dict.get("fiftyTwoWeekLow") or getattr(info, "year_low", price)
                    )
                except Exception:
                    market_cap = 0.0
                    week_52_high = getattr(info, "year_high", price)
                    week_52_low = getattr(info, "year_low", price)

                open_p = price
                high = price
                low = price
                volume = 0
                prev_close = price

            return {
                "symbol": sym,
                "price": price,
                "open": open_p,
                "high": high,
                "low": low,
                "volume": volume,
                "previous_close": prev_close,
                "market_cap": market_cap if price is not None else 0.0,
                "week_52_high": week_52_high if price is not None else None,
                "week_52_low": week_52_low if price is not None else None,
                "source": "yfinance",
            }

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
                result = await asyncio.wait_for(asyncio.to_thread(_fetch_quote), timeout=8.0)

            if not result or result.get("price") is None:
                # Async fallback to get_history if fast_info didn't work
                hist = await MarketDataService.get_history(sym, interval="1d", period="5d")
                if not hist:
                    raise ValueError(sym)

                # Update result with history
                price = float(hist[-1]["close"])
                prev_close = float(hist[-2]["close"]) if len(hist) >= 2 else price
                result = {
                    "symbol": sym,
                    "price": price,
                    "open": float(hist[-1]["open"]),
                    "high": float(hist[-1]["high"]),
                    "low": float(hist[-1]["low"]),
                    "volume": int(hist[-1].get("volume", 0)),
                    "previous_close": prev_close,
                    "market_cap": 0.0,
                    "week_52_high": float(hist[-1]["high"]),
                    "week_52_low": float(hist[-1]["low"]),
                    "source": "yfinance",
                }

            # Format numbers properly before returning
            price = result["price"]
            prev_close = result["previous_close"]
            change = price - prev_close
            change_pct = (change / prev_close * 100.0) if prev_close != 0.0 else 0.0

            result.update(
                {
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 4),
                    "open": round(result["open"], 2),
                    "high": round(result["high"], 2),
                    "low": round(result["low"], 2),
                    "previous_close": round(prev_close, 2),
                }
            )
            if result.get("week_52_high"):
                result["week_52_high"] = round(result["week_52_high"], 2)
            if result.get("week_52_low"):
                result["week_52_low"] = round(result["week_52_low"], 2)

        except Exception as e:
            # Attempt fallback using IndianStockAPI (0xramm) before caching failure
            try:
                fallback = IndianStockAPI.fetch_quote(sym)
                if fallback:
                    # Cache fallback result
                    if redis:
                        await redis.setex(cache_key, 60, json.dumps(fallback))
                    return fallback
            except Exception as fe:
                logger.debug(f"IndianStockAPI fallback failed for {sym}: {fe}")

            # Tombstone / cache the failure so we don't spam network
            datetime.now(UTC).timestamp()
            failure_dict = {"error": True, "message": str(e)}
            if redis:
                try:
                    await redis.setex(cache_key, 60, json.dumps(failure_dict))
                except Exception:
                    pass
            if isinstance(e, ValueError):
                raise
            raise ValueError(sym) from e
            # Tombstone / cache the failure so we don't spam network
            datetime.now(UTC).timestamp()
            failure_dict = {"error": True, "message": str(e)}
            if redis:
                try:
                    await redis.setex(cache_key, 60, json.dumps(failure_dict))
                except Exception:
                    pass
            if isinstance(e, ValueError):
                raise
            raise ValueError(sym) from e

        # Store in caches
        datetime.now(UTC).timestamp()
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

        # D8: Never silently relabel data. Use exact intervals supported by yfinance.
        # Fallback mappings only for identical semantic meanings.
        yf_interval = "1wk" if interval == "1w" else interval

        # D9: yfinance interval/period limits
        if interval == "1m" and period not in ("1d", "5d"):
            period = "5d"
        elif interval in ("2m", "5m", "15m", "30m", "1h", "60m") and period in (
            "max",
            "10y",
            "5y",
            "2y",
            "1y",
        ):
            period = "60d"

        cache_key = f"mds:history:{sym}:{yf_interval}:{period}"
        datetime.now(UTC).timestamp()

        redis = None
        try:
            from app.database.redis_client import get_redis_client

            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                if isinstance(cached_data, dict) and cached_data.get("error"):
                    return []
                if isinstance(cached_data, dict) and "bars" in cached_data:
                    res_list = HistoryList(
                        cached_data["bars"], source=cached_data.get("source", "yfinance")
                    )
                    return res_list
                else:
                    res_list = HistoryList(cached_data, source="yfinance")
                    return res_list
        except Exception as re:
            logger.warning(f"Redis cache check failed for get_history key={cache_key}: {re}")

        def _fetch_history() -> list[dict]:
            import pandas as pd

            session = MarketDataService.get_session()
            try:
                df = yf.download(
                    sym,
                    period=period,
                    interval=yf_interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    session=session,
                )
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
                bars.append(
                    {
                        "time": time_str,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row.get("Volume", 0.0) or 0.0),
                    }
                )

            if bars:
                print(
                    f"[HOP 1 yfinance] {sym} @ {interval}: count_out={len(bars)}, first={bars[0]['time']}, last={bars[-1]['time']}"
                )
            return bars

        result = None
        try:
            from datetime import timedelta

            from app.services.data_ingestion.orchestrator import (
                DataIngestionOrchestrator,
                IngestionTask,
            )

            # D8: Never silently relabel data
            orch_interval = interval

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
                asset_type=asset_type,
            )
            orchestrator = DataIngestionOrchestrator(max_concurrency=4)
            source_name, ohlcv_bars = await orchestrator.fetch_task(task)
            if ohlcv_bars:
                bars_list = []
                for b in ohlcv_bars:
                    time_str = b.time.isoformat() if hasattr(b.time, "isoformat") else str(b.time)
                    bars_list.append(
                        {
                            "time": time_str,
                            "open": float(b.open),
                            "high": float(b.high),
                            "low": float(b.low),
                            "close": float(b.close),
                            "volume": float(b.volume),
                        }
                    )
                if bars_list:
                    print(
                        f"[HOP 1 {source_name}] {sym} @ {interval}: count_out={len(bars_list)}, first={bars_list[0]['time']}, last={bars_list[-1]['time']}"
                    )
                result = HistoryList(bars_list, source=source_name)
                logger.info(
                    f"Historical data fetched via orchestrator source: {source_name} for {sym}"
                )
        except Exception as e:
            logger.info(
                f"Orchestrator fetch failed for {sym}: {e}, falling back to direct yfinance..."
            )

        if not result:
            try:
                async with MarketDataService._semaphore:
                    raw_bars = await asyncio.wait_for(
                        asyncio.to_thread(_fetch_history), timeout=10.0
                    )
                if raw_bars:
                    result = HistoryList(raw_bars, source="yfinance")
                    logger.info(f"Historical data fallback fetched via yfinance for {sym}")
            except Exception as e:
                logger.warning(f"yfinance download failed for {sym}: {e}")
                result = None

        datetime.now(UTC).timestamp()
        if not result:
            failure_dict = {"error": True}
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(failure_dict))
                except Exception:
                    pass
        else:
            cache_payload = {"source": result.source, "bars": list(result)}
            if redis:
                try:
                    await redis.setex(cache_key, 300, json.dumps(cache_payload))
                except Exception as se:
                    logger.warning(f"Redis cache set failed for get_history key={cache_key}: {se}")

        if result:
            bars_for_log = list(result) if not hasattr(result, "bars") else result.bars
            print(
                f"[HOP 2 MarketDataService] {sym} @ {interval}: count_out={len(bars_for_log)}, first={bars_for_log[0]['time'] if bars_for_log else 'None'}, last={bars_for_log[-1]['time'] if bars_for_log else 'None'}"
            )
        else:
            print(f"[HOP 2 MarketDataService] {sym} @ {interval}: count_out=0")
        return result

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

    @staticmethod
    async def get_movers(n: int = 10, mover_type: str = "gainers") -> list[dict]:
        """Fetch quotes concurrently for NIFTY 50 symbol roots.

        Sorts by change_pct and returns top n.
        """
        symbols = MarketDataService.NSE_NIFTY50

        tasks = [MarketDataService.get_quote(sym) for sym in symbols]
        quotes_res = await asyncio.gather(*tasks, return_exceptions=True)

        quotes = []
        for sym, q in zip(symbols, quotes_res, strict=False):
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
            movers.append(
                {
                    "ticker": q["symbol"],
                    "name": q["symbol"].split(".")[0],
                    "price": q["price"],
                    "change_pct": q["change_pct"],
                    "volume": q["volume"],
                    "rank": i + 1,
                }
            )
        return movers

    @staticmethod
    async def get_indices() -> list[dict]:
        """Fetch quotes for ^NSEI, ^BSESN, and ^NSEBANK concurrently.

        Maps ticker symbols to display names: NIFTY 50, BSE Sensex, Bank Nifty.
        """
        index_symbols = ["^NSEI", "^BSESN", "^NSEBANK"]
        tasks = [MarketDataService.get_quote(sym) for sym in index_symbols]
        res = await asyncio.gather(*tasks, return_exceptions=True)

        names_map = {"^NSEI": "NIFTY 50", "^BSESN": "BSE Sensex", "^NSEBANK": "Bank Nifty"}

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

    @staticmethod
    async def get_nifty50_movers() -> dict:
        """Get top gainers and losers from Nifty 50 — free via yfinance batch."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, MarketDataService._fetch_movers_sync)

    @staticmethod
    def _fetch_movers_sync() -> dict:
        # Batch download is faster than individual calls
        data = yf.download(
            MarketDataService.NSE_NIFTY50,
            period="2d",
            interval="1d",
            group_by="ticker",
            progress=False,
        )

        movers = []
        for sym in MarketDataService.NSE_NIFTY50:
            try:
                sym_data = data[sym] if sym in data.columns.get_level_values(0) else None
                if sym_data is not None and len(sym_data) >= 2:
                    today = float(sym_data["Close"].iloc[-1])
                    yesterday = float(sym_data["Close"].iloc[-2])
                    chg_pct = ((today - yesterday) / yesterday) * 100
                    movers.append(
                        {
                            "symbol": sym.replace(".NS", ""),
                            "price": today,
                            "change_pct": round(chg_pct, 2),
                        }
                    )
            except Exception:
                continue

        movers_sorted = sorted(movers, key=lambda x: x["change_pct"], reverse=True)
        return {"gainers": movers_sorted[:5], "losers": movers_sorted[-5:][::-1]}
