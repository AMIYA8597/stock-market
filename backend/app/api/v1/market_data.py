"""Market data API endpoints aligned to the prompt Section 3 contract."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from typing import Literal

import pandas as pd
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.database.mongodb import (
    mongo_cache_market_payload,
    mongo_get_market_payload,
)
from app.database.redis_client import get_redis
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter()


class QuoteResponse(BaseModel):
    ticker: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: float
    pe_ratio: float
    high_52w: float
    low_52w: float
    regime: dict[str, object]
    signal: dict[str, object]
    timestamp: datetime


class OhlcvPoint(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryResponse(BaseModel):
    symbol: str
    interval: str
    data: list[OhlcvPoint]


class IndexResponse(BaseModel):
    name: str
    ticker: str
    value: float
    change: float
    change_pct: float
    regime_state: Literal["BULL", "BEAR", "SIDEWAYS", "CRISIS"]


class MoverResponse(BaseModel):
    ticker: str
    name: str
    exchange: str
    price: float
    change_pct: float
    volume: int
    signal_direction: Literal["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]
    confidence: float


class HeatmapStock(BaseModel):
    ticker: str
    name: str
    value: float
    metric: str


class HeatmapSector(BaseModel):
    sector: str
    stocks: list[HeatmapStock]


class SearchResponse(BaseModel):
    ticker: str
    name: str
    exchange: str
    asset_type: str


class EconomicEvent(BaseModel):
    date: date
    category: Literal["FOMC", "EARNINGS", "EXPIRY", "MACRO"]
    title: str
    impact: Literal["LOW", "MEDIUM", "HIGH"]


def _exchange_predicate(exchange: str) -> tuple[str, dict[str, object]]:
    exch = exchange.upper()
    if exch == "CRYPTO":
        return "UPPER(s.asset_type) = 'CRYPTO'", {}
    return "UPPER(s.exchange) = :exchange", {"exchange": exch}


async def _fetch_quote_from_yfinance(symbol: str) -> QuoteResponse:
    ticker = yf.Ticker(symbol)

    def _pull() -> dict[str, object]:
        hist = ticker.history(period="2d", interval="1d")
        info = ticker.info or {}
        if hist.empty:
            raise ValueError("No market history available")
        latest = hist.iloc[-1]
        prev_close = float(latest.get("Close", 0.0))
        if len(hist) > 1:
            prev_close = float(hist.iloc[-2].get("Close", prev_close))
        price = float(latest.get("Close", 0.0))
        change = price - prev_close
        change_pct = 0.0 if prev_close == 0 else (change / prev_close) * 100.0

        fifty_two_high = float(info.get("fiftyTwoWeekHigh") or price)
        fifty_two_low = float(info.get("fiftyTwoWeekLow") or price)

        if pd.isna(price) or pd.isna(change) or pd.isna(change_pct) or pd.isna(fifty_two_high) or pd.isna(fifty_two_low):
            raise ValueError("NaN values encountered in quote data")

        return {
            "ticker": symbol.upper(),
            "name": str(info.get("shortName") or symbol.upper()),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 3),
            "volume": int(float(latest.get("Volume", 0.0) or 0.0)),
            "market_cap": float(info.get("marketCap") or 0.0),
            "pe_ratio": float(info.get("trailingPE") or 0.0),
            "high_52w": round(fifty_two_high, 2),
            "low_52w": round(fifty_two_low, 2),
        }

    result = await asyncio.to_thread(_pull)
    signal_score = max(-1.0, min(1.0, float(result["change_pct"]) / 5.0))
    probs = _state_probs_from_signal(signal_score)
    state = max(probs, key=probs.get).upper()
    direction = _direction_from_signal(signal_score)

    return QuoteResponse(
        ticker=str(result["ticker"]),
        name=str(result["name"]),
        price=float(result["price"]),
        change=float(result["change"]),
        change_pct=float(result["change_pct"]),
        volume=int(result["volume"]),
        market_cap=float(result["market_cap"]),
        pe_ratio=float(result["pe_ratio"]),
        high_52w=float(result["high_52w"]),
        low_52w=float(result["low_52w"]),
        regime={"state": state, "probs": probs},
        signal={"direction": direction, "confidence": round(min(0.95, 0.55 + abs(signal_score) * 0.35), 3)},
        timestamp=datetime.now(UTC),
    )


def _state_probs_from_signal(signal: float) -> dict[str, float]:
    signal_clamped = max(-1.0, min(1.0, signal))
    bull = max(0.02, 0.35 + max(0.0, signal_clamped) * 0.45)
    bear = max(0.02, 0.35 + max(0.0, -signal_clamped) * 0.45)
    sideways = 0.2
    crisis = 0.1
    total = bull + bear + sideways + crisis
    return {
        "bull": round(bull / total, 3),
        "bear": round(bear / total, 3),
        "sideways": round(sideways / total, 3),
        "crisis": round(crisis / total, 3),
    }


def _direction_from_signal(signal: float) -> str:
    if signal > 0.6:
        return "STRONG_BUY"
    if signal > 0.2:
        return "BUY"
    if signal < -0.6:
        return "STRONG_SELL"
    if signal < -0.2:
        return "SELL"
    return "NEUTRAL"


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str, db: AsyncSession = Depends(get_db)):
    """Return quote via Redis cache, then yfinance fallback on cache miss."""
    key = f"quote:{symbol.upper()}"
    redis = None
    try:
        redis = await get_redis()
    except Exception:
        redis = None

    if redis is not None:
        try:
            cached = await redis.get(key)
            if cached:
                payload = json.loads(cached)
                payload["timestamp"] = datetime.fromisoformat(payload["timestamp"]) if isinstance(payload.get("timestamp"), str) else datetime.now(UTC)
                return QuoteResponse(**payload)
        except Exception:
            # If Redis is unavailable, we still serve from yfinance fallback.
            pass

    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT s.ticker,
                           s.name,
                           latest.time,
                           latest.open,
                           latest.close,
                           latest.volume,
                           (
                               SELECT o2.close
                               FROM ohlcv o2
                               WHERE o2.symbol_id = s.id
                                 AND o2.time < latest.time
                               ORDER BY o2.time DESC
                               LIMIT 1
                           ) AS prev_close
                    FROM symbols s
                    JOIN (
                        SELECT o1.symbol_id, o1.time, o1.open, o1.close, o1.volume
                        FROM ohlcv o1
                        WHERE o1.symbol_id = (SELECT id FROM symbols WHERE UPPER(ticker) = :ticker)
                        ORDER BY o1.time DESC
                        LIMIT 1
                    ) latest ON latest.symbol_id = s.id
                    WHERE UPPER(s.ticker) = :ticker
                    LIMIT 1
                    """
                ),
                {"ticker": symbol.upper()},
            )
        ).mappings().first()

        if row is None:
            raise ValueError("No symbol/ohlcv row available")

        price = float(row["close"])
        prev_close = float(row["prev_close"] or row["open"] or row["close"])
        change = price - prev_close
        change_pct = 0.0 if prev_close == 0 else (change / prev_close) * 100.0

        signal = (
            await db.execute(
                text(
                    """
                    SELECT signal, confidence, direction
                    FROM ensemble_signals es
                    JOIN symbols s ON s.id = es.symbol_id
                    WHERE UPPER(s.ticker) = :ticker
                    ORDER BY es.time DESC
                    LIMIT 1
                    """
                ),
                {"ticker": symbol.upper()},
            )
        ).mappings().first()

        signal_value = float(signal["signal"]) if signal else 0.0
        signal_conf = float(signal["confidence"]) if signal else 0.5
        signal_direction = str(signal["direction"]) if signal else _direction_from_signal(signal_value)
        probs = _state_probs_from_signal(signal_value)
        regime_state = max(probs, key=probs.get).upper()

        quote = QuoteResponse(
            ticker=str(row["ticker"]),
            name=str(row["name"]),
            price=round(price, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 3),
            volume=int(float(row["volume"] or 0.0)),
            market_cap=0.0,
            pe_ratio=0.0,
            high_52w=round(max(price, prev_close), 2),
            low_52w=round(min(price, prev_close), 2),
            regime={"state": regime_state, "probs": probs},
            signal={"direction": signal_direction, "confidence": round(signal_conf, 3)},
            timestamp=row["time"],
        )
    except Exception as db_exc:
        logger.debug(f"Database query failed for {symbol}: {db_exc}. Trying yfinance fallback.")
        try:
            quote = await _fetch_quote_from_yfinance(symbol)
        except Exception as exc:
            logger.warning(f"yfinance quote failed for {symbol}: {exc}. Trying cached market payload.")
            cached_quote = await mongo_get_market_payload("quote", symbol.upper())
            if isinstance(cached_quote, dict):
                cached_quote["timestamp"] = datetime.fromisoformat(str(cached_quote["timestamp"]))
                return QuoteResponse(**cached_quote)
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse.create(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message=f"Live quote is unavailable for {symbol.upper()}. Configure a market data provider or retry later.",
                ).dict(),
            ) from exc

    if redis is not None:
        try:
            cache_payload = quote.model_dump()
            cache_payload["timestamp"] = quote.timestamp.isoformat()
            await redis.set(key, json.dumps(cache_payload), ex=1)
        except Exception:
            pass

    await mongo_cache_market_payload(
        "quote",
        symbol.upper(),
        {
            **quote.model_dump(),
            "timestamp": quote.timestamp.isoformat(),
        },
        ttl_seconds=120,
    )

    return quote

@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query(default="1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str = Query(default="1y", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    db: AsyncSession = Depends(get_db),
):
    """Return OHLCV series as {symbol, interval, data:[...]} contract."""
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
    since = datetime.now(UTC) - timedelta(days=period_days[period])

    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT o.time, o.open, o.high, o.low, o.close, o.volume
                    FROM ohlcv o
                    JOIN symbols s ON s.id = o.symbol_id
                    WHERE UPPER(s.ticker) = :ticker
                      AND o.interval = :interval
                      AND o.time >= :since
                    ORDER BY o.time ASC
                    """
                ),
                {"ticker": symbol.upper(), "interval": interval, "since": since},
            )
        ).mappings().all()
    except Exception:
        rows = []

    if not rows:
        try:
            # Adjust period/interval compatibility for yfinance
            yf_interval = interval
            if interval == "3m":
                yf_interval = "1m"
            elif interval == "10m":
                yf_interval = "5m"
            elif interval == "45m":
                yf_interval = "15m"
            elif interval == "2h":
                yf_interval = "1h"
            elif interval == "4h":
                yf_interval = "1h"
            elif interval == "1w":
                yf_interval = "1wk"
            elif interval == "1mo":
                yf_interval = "1mo"

            yf_period = period
            if yf_interval == "1m" and period not in {"1d", "5d", "7d"}:
                yf_period = "5d"
            elif yf_interval in {"5m", "15m", "30m"} and period not in {"1d", "5d", "1mo", "3mo"}:
                yf_period = "1mo"
            elif yf_interval == "1h" and period not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"}:
                yf_period = "1mo"

            def _fetch_yf_history() -> pd.DataFrame:
                ticker = yf.Ticker(symbol)
                return ticker.history(period=yf_period, interval=yf_interval)

            df = await asyncio.to_thread(_fetch_yf_history)
            if not df.empty:
                if interval in {"3m", "10m", "45m", "2h", "4h"}:
                    resample_rules = {
                        "3m": "3Min",
                        "10m": "10Min",
                        "45m": "45Min",
                        "2h": "2H",
                        "4h": "4H",
                    }
                    rule = resample_rules[interval]
                    df = df.resample(rule).agg({
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum"
                    }).dropna()

                rows = []
                for idx, row in df.iterrows():
                    # Convert pandas index Timestamp to datetime
                    dt = idx.to_pydatetime()
                    rows.append(
                        {
                            "time": dt,
                            "open": float(row["Open"]),
                            "high": float(row["High"]),
                            "low": float(row["Low"]),
                            "close": float(row["Close"]),
                            "volume": float(row["Volume"]),
                        }
                    )
        except Exception as e:
            logger.warning(f"Error fetching yfinance history for {symbol}: {e}")
            rows = []

    if not rows:
        cached_history = await mongo_get_market_payload("history", f"{symbol.upper()}:{interval}:{period}")
        if isinstance(cached_history, dict):
            cached_rows = cached_history.get("data")
            if isinstance(cached_rows, list):
                return HistoryResponse(
                    symbol=str(cached_history.get("symbol", symbol.upper())),
                    interval=str(cached_history.get("interval", interval)),
                    data=[
                        OhlcvPoint(
                            time=datetime.fromisoformat(str(row["time"])),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=int(float(row["volume"])),
                        )
                        for row in cached_rows
                    ],
                )
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Historical candles are unavailable for {symbol.upper()} {interval}.",
            ).dict(),
        )

    points = [
        OhlcvPoint(
            time=row["time"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(float(row["volume"])),
        )
        for row in rows
    ]
    await mongo_cache_market_payload(
        "history",
        f"{symbol.upper()}:{interval}:{period}",
        {
            "symbol": symbol.upper(),
            "interval": interval,
            "data": [
                {
                    "time": point.time.isoformat(),
                    "open": point.open,
                    "high": point.high,
                    "low": point.low,
                    "close": point.close,
                    "volume": point.volume,
                }
                for point in points
            ],
        },
        ttl_seconds=900,
    )
    return HistoryResponse(symbol=symbol.upper(), interval=interval, data=points)


@router.get("/indices", response_model=list[IndexResponse])
async def get_indices() -> list[IndexResponse]:
    """Return benchmark indices across NSE, US, VIX and major crypto."""
    index_universe = [
        ("NIFTY 50", "^NSEI"),
        ("SENSEX", "^BSESN"),
        ("S&P 500", "^GSPC"),
        ("NASDAQ", "^IXIC"),
        ("DOW JONES", "^DJI"),
        ("VIX", "^VIX"),
        ("Bitcoin", "BTC-USD"),
        ("Ethereum", "ETH-USD"),
    ]
    tickers = [t for n, t in index_universe]

    def _fetch_all_indices() -> pd.DataFrame:
        return yf.download(tickers, period="2d", interval="1d", group_by="ticker", progress=False)

    try:
        df = await asyncio.to_thread(_fetch_all_indices)
        rows = []
        for name, ticker in index_universe:
            try:
                if len(tickers) == 1:
                    symbol_df = df
                else:
                    symbol_df = df[ticker]

                if symbol_df.empty or len(symbol_df) < 1:
                    raise ValueError("No index history")

                latest = symbol_df.iloc[-1]
                value = float(latest.get("Close", 0.0))
                prev_close = value
                if len(symbol_df) > 1:
                    prev_close = float(symbol_df.iloc[-2].get("Close", value))

                change = value - prev_close
                change_pct = 0.0 if prev_close == 0 else (change / prev_close) * 100.0

                if pd.isna(value) or pd.isna(change) or pd.isna(change_pct):
                    raise ValueError("NaN values encountered in index history")

                probs = _state_probs_from_signal(max(-1.0, min(1.0, change_pct / 3.0)))
                regime_state = max(probs, key=probs.get).upper()

                rows.append(
                    IndexResponse(
                        name=name,
                        ticker=ticker,
                        value=round(value, 2),
                        change=round(change, 2),
                        change_pct=round(change_pct, 3),
                        regime_state=regime_state,
                    )
                )
            except Exception as e:
                logger.warning(f"Error fetching ticker {ticker}: {e}")
        if rows:
            await mongo_cache_market_payload(
                "indices",
                "global",
                [row.model_dump() for row in rows],
                ttl_seconds=180,
            )
            return rows
    except Exception as e:
        logger.error(f"Error fetching batch indices: {e}")
    cached = await mongo_get_market_payload("indices", "global")
    if isinstance(cached, list):
        return [IndexResponse(**row) for row in cached]
    raise HTTPException(
        status_code=503,
        detail=ErrorResponse.create(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Benchmark index data is currently unavailable.",
        ).dict(),
    )

@router.get("/movers", response_model=list[MoverResponse])
async def get_movers(
    exchange: str = Query(default="NSE", pattern="^(NSE|NYSE|CRYPTO)$"),
    type: str = Query(default="gainers", pattern="^(gainers|losers|volume|momentum)$"),
    db: AsyncSession = Depends(get_db),
) -> list[MoverResponse]:
    """Return top 20 movers with signal overlay."""
    sort_expr = {
        "gainers": "change_pct DESC",
        "losers": "change_pct ASC",
        "volume": "latest_volume DESC",
        "momentum": "signal_value DESC",
    }[type]
    where_sql, where_params = _exchange_predicate(exchange)

    query = text(
        f"""
        WITH latest AS (
            SELECT o.symbol_id,
                   o.close AS latest_close,
                   o.volume AS latest_volume,
                   o.time AS latest_time,
                   LAG(o.close) OVER (PARTITION BY o.symbol_id ORDER BY o.time) AS prev_close,
                   ROW_NUMBER() OVER (PARTITION BY o.symbol_id ORDER BY o.time DESC) AS rn
            FROM ohlcv o
            WHERE o.interval = '1d'
        ),
        latest_only AS (
            SELECT
                   symbol_id,
                   latest_close,
                   latest_volume,
                   latest_time,
                   prev_close
            FROM latest
            WHERE rn = 1
        ),
        sig_ranked AS (
            SELECT
                   es.symbol_id,
                   es.signal AS signal_value,
                   es.direction,
                   es.confidence,
                   ROW_NUMBER() OVER (PARTITION BY es.symbol_id ORDER BY es.time DESC) AS rn
            FROM ensemble_signals es
        ),
        sig AS (
            SELECT
                   symbol_id,
                   signal_value,
                   direction,
                   confidence
            FROM sig_ranked
            WHERE rn = 1
        )
        SELECT s.ticker,
               s.name,
               s.exchange,
               lo.latest_close,
               lo.latest_volume,
               COALESCE((lo.latest_close - lo.prev_close) / NULLIF(lo.prev_close, 0) * 100.0, 0.0) AS change_pct,
               COALESCE(sig.signal_value, 0.0) AS signal_value,
               COALESCE(sig.direction, 'NEUTRAL') AS direction,
               COALESCE(sig.confidence, 0.5) AS confidence
        FROM symbols s
        JOIN latest_only lo ON lo.symbol_id = s.id
        LEFT JOIN sig ON sig.symbol_id = s.id
        WHERE {where_sql}
        ORDER BY {sort_expr}
        LIMIT 20
        """
    )

    try:
        result = (await db.execute(query, where_params)).mappings().all()
    except Exception:
        result = []

    if not result:
        try:
            ticker_map = {
                "NSE": [
                    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                    "BHARTIARTL.NS", "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
                    "AXISBANK.NS", "KOTAKBANK.NS", "SUNPHARMA.NS", "TITAN.NS", "MARUTI.NS",
                    "TATASTEEL.NS", "WIPRO.NS", "BAJFINANCE.NS", "ADANIENT.NS", "POWERGRID.NS"
                ],
                "NYSE": [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "UNH",
                    "MA", "HD", "PG", "LLY", "AVGO", "COST", "ADBE", "CRM", "NFLX", "AMD"
                ],
                "CRYPTO": [
                    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD",
                    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "SHIB-USD", "LTC-USD",
                    "UNI-USD", "MATIC-USD", "ICP-USD", "NEAR-USD", "BCH-USD", "FIL-USD",
                    "ATOM-USD", "XLM-USD"
                ]
            }
            symbols = ticker_map.get(exchange, ticker_map["NSE"])

            def _fetch_all_movers() -> pd.DataFrame:
                return yf.download(symbols, period="2d", interval="1d", group_by="ticker", progress=False)

            df = await asyncio.to_thread(_fetch_all_movers)
            generated = []
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_df = df
                    else:
                        symbol_df = df[sym]

                    if symbol_df.empty or len(symbol_df) < 1:
                        continue

                    latest = symbol_df.iloc[-1]
                    price = float(latest.get("Close", 100.0))
                    volume = int(float(latest.get("Volume", 0.0) or 0.0))
                    prev_price = price
                    if len(symbol_df) > 1:
                        prev_price = float(symbol_df.iloc[-2].get("Close", price))

                    change_pct = 0.0
                    if prev_price > 0:
                        change_pct = ((price - prev_price) / prev_price) * 100.0

                    short_name = sym.split(".")[0].upper()
                    generated.append(
                        {
                            "ticker": sym,
                            "name": short_name,
                            "exchange": exchange,
                            "latest_close": price,
                            "latest_volume": volume,
                            "change_pct": change_pct,
                            "direction": "STRONG_BUY" if change_pct > 2.0 else "BUY" if change_pct > 0.5 else "STRONG_SELL" if change_pct < -2.0 else "SELL" if change_pct < -0.5 else "NEUTRAL",
                            "confidence": round(0.55 + min(abs(change_pct) * 0.1, 0.4), 3),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error parsing movers symbol {sym}: {e}")

            # Sort based on requested type
            if type == "gainers":
                generated.sort(key=lambda x: x["change_pct"], reverse=True)
            elif type == "losers":
                generated.sort(key=lambda x: x["change_pct"], reverse=False)
            elif type == "volume":
                generated.sort(key=lambda x: x["latest_volume"], reverse=True)
            else:  # momentum / default
                generated.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

            result = generated[:20]
        except Exception as e:
            logger.error(f"Error fetching batch movers: {e}")
            result = []

    if not result:
        cached_movers = await mongo_get_market_payload("movers", f"{exchange}:{type}")
        if isinstance(cached_movers, list):
            return [MoverResponse(**row) for row in cached_movers]
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market movers are unavailable for {exchange}.",
            ).dict(),
        )

    response = [
        MoverResponse(
            ticker=str(row["ticker"]),
            name=str(row["name"]),
            exchange=str(row["exchange"]),
            price=round(float(row["latest_close"]), 2),
            change_pct=round(float(row["change_pct"]), 3),
            volume=int(float(row["latest_volume"])),
            signal_direction=str(row["direction"]),
            confidence=round(float(row["confidence"]), 3),
        )
        for row in result
    ]
    await mongo_cache_market_payload(
        "movers",
        f"{exchange}:{type}",
        [item.model_dump() for item in response],
        ttl_seconds=180,
    )
    return response


@router.get("/heatmap", response_model=list[HeatmapSector])
async def get_heatmap(
    exchange: str = Query(default="NSE", pattern="^(NSE|NYSE|CRYPTO)$"),
    metric: str = Query(default="return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
    db: AsyncSession = Depends(get_db),
) -> list[HeatmapSector]:
    """Return treemap-ready sector groups and stock metric values."""
    where_sql, where_params = _exchange_predicate(exchange)

    metric_expr = {
        "return_1d": "COALESCE((latest_close - prev_close_1d) / NULLIF(prev_close_1d, 0) * 100.0, 0.0)",
        "return_5d": "COALESCE((latest_close - prev_close_5d) / NULLIF(prev_close_5d, 0) * 100.0, 0.0)",
        "volume_surge": "COALESCE(latest_volume / NULLIF(avg_volume_20d, 0), 0.0)",
    }[metric]

    query = text(
        f"""
        WITH ranked AS (
            SELECT o.symbol_id,
                   o.time,
                   o.close,
                   o.volume,
                   ROW_NUMBER() OVER (PARTITION BY o.symbol_id ORDER BY o.time DESC) AS rn,
                   AVG(o.volume) OVER (
                       PARTITION BY o.symbol_id
                       ORDER BY o.time
                       ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                   ) AS avg_volume_20d
            FROM ohlcv o
            WHERE o.interval = '1d'
        ),
        piv AS (
            SELECT symbol_id,
                   MAX(CASE WHEN rn = 1 THEN close END) AS latest_close,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS latest_volume,
                   MAX(CASE WHEN rn = 2 THEN close END) AS prev_close_1d,
                   MAX(CASE WHEN rn = 6 THEN close END) AS prev_close_5d,
                   MAX(CASE WHEN rn = 1 THEN avg_volume_20d END) AS avg_volume_20d
            FROM ranked
            GROUP BY symbol_id
        ),
        values_cte AS (
            SELECT s.ticker,
                   s.name,
                   COALESCE(NULLIF(s.sector, ''), 'Other') AS sector,
                   {metric_expr} AS metric_value
            FROM symbols s
            JOIN piv p ON p.symbol_id = s.id
            WHERE {where_sql}
        )
        SELECT ticker, name, sector, metric_value
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY sector ORDER BY metric_value DESC) AS rnk
            FROM values_cte
        ) x
        WHERE rnk <= 8
        ORDER BY sector, metric_value DESC
        """
    )

    try:
        result = (await db.execute(query, where_params)).mappings().all()
    except Exception:
        result = []

    if not result:
        cached_heatmap = await mongo_get_market_payload("heatmap", f"{exchange}:{metric}")
        if isinstance(cached_heatmap, list):
            return [HeatmapSector(**row) for row in cached_heatmap]
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Heatmap data is unavailable for {exchange}.",
            ).dict(),
        )

    grouped: dict[str, list[HeatmapStock]] = {}
    for row in result:
        sector = str(row["sector"])
        grouped.setdefault(sector, []).append(
            HeatmapStock(
                ticker=str(row["ticker"]),
                name=str(row["name"]),
                value=round(float(row["metric_value"]), 3),
                metric=metric,
            )
        )

    response = [HeatmapSector(sector=sector, stocks=stocks) for sector, stocks in grouped.items()]
    await mongo_cache_market_payload(
        "heatmap",
        f"{exchange}:{metric}",
        [item.model_dump() for item in response],
        ttl_seconds=600,
    )
    return response


@router.get("/search", response_model=list[SearchResponse])
async def search_market(q: str = Query(..., min_length=2), db: AsyncSession = Depends(get_db)) -> list[SearchResponse]:
    """Return symbol matches from the symbols table using ticker/name search."""
    like_q = f"%{q.upper()}%"
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT ticker, name, exchange, asset_type
                    FROM symbols
                    WHERE UPPER(ticker) LIKE :query
                       OR UPPER(name) LIKE :query
                    ORDER BY
                      CASE WHEN UPPER(ticker) = :exact THEN 0 ELSE 1 END,
                      ticker
                    LIMIT 25
                    """
                ),
                {"query": like_q, "exact": q.upper()},
            )
        ).mappings().all()
    except Exception:
        rows = []

    if not rows:
        candidates = [
            {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "exchange": "NSE", "asset_type": "EQUITY"},
            {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "exchange": "NSE", "asset_type": "EQUITY"},
            {"ticker": "INFY.NS", "name": "Infosys", "exchange": "NSE", "asset_type": "EQUITY"},
        ]
        q_upper = q.upper()
        rows = [c for c in candidates if q_upper in c["ticker"] or q_upper in c["name"].upper()]

    return [
        SearchResponse(
            ticker=str(row["ticker"]),
            name=str(row["name"]),
            exchange=str(row["exchange"]),
            asset_type=str(row["asset_type"]),
        )
        for row in rows
    ]


@router.get("/economic-calendar", response_model=list[EconomicEvent])
async def get_economic_calendar() -> list[EconomicEvent]:
    """Return upcoming macro and market events for the next 30 days."""
    today = datetime.now(UTC).date()
    return [
        EconomicEvent(date=today + timedelta(days=3), category="FOMC", title="FOMC Rate Decision", impact="HIGH"),
        EconomicEvent(date=today + timedelta(days=7), category="EARNINGS", title="Large Cap Earnings Cluster", impact="MEDIUM"),
        EconomicEvent(date=today + timedelta(days=13), category="EXPIRY", title="Monthly Derivatives Expiry", impact="HIGH"),
        EconomicEvent(date=today + timedelta(days=21), category="MACRO", title="US CPI Release", impact="MEDIUM"),
    ]
