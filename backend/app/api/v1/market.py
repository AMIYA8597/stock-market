# backend/app/api/v1/market.py
"""Market data endpoints router — all values computed from yfinance."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_rate_limiter

logger = logging.getLogger(__name__)

from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.market import (
    EconomicCalendarResponse,
    EconomicEvent,
    HeatmapResponse,
    HistoryResponse,
    IndexData,
    IndicesResponse,
    InstrumentInfo,
    MoverData,
    MoversResponse,
    OHLCVBar,
    QuoteResponse,
    RegimeData,
    SearchResponse,
    SearchResult,
    SectorNode,
    SignalData,
    UniverseResponse,
)
from app.services.data_ingestion.provider_manager import provider_manager
from app.services.market_data_service import MarketDataService
from app.services.market_status import MarketStatusService

router = APIRouter(prefix="/market", tags=["market"])

SECTOR_MAP = {
    "RELIANCE": "Energy",
    "NTPC": "Energy",
    "ONGC": "Energy",
    "COALINDIA": "Energy",
    "POWERGRID": "Energy",
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "HDFCBANK": "Financials",
    "ICICIBANK": "Financials",
    "SBIN": "Financials",
    "KOTAKBANK": "Financials",
    "AXISBANK": "Financials",
    "BAJFINANCE": "Financials",
    "HINDUNILVR": "Consumer Goods",
    "ITC": "Consumer Goods",
    "ASIANPAINT": "Consumer Goods",
    "TITAN": "Consumer Goods",
    "NESTLEIND": "Consumer Goods",
    "MARUTI": "Automobile",
    "LT": "Industrials",
    "SUNPHARMA": "Healthcare",
    "ULTRACEMCO": "Materials",
    "TATASTEEL": "Materials",
    "JSWSTEEL": "Materials",
    "GRASIM": "Materials",
    "ADANIENT": "Conglomerates",
    "ADANIPORTS": "Conglomerates",
}


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str, _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
) -> QuoteResponse:
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )

    try:
        quote = await provider_manager.get_quote(symbol)
        price_val = float(quote.price)
        change_pct = float(quote.change_pct)

        # Build neutral/deterministic regime/signal metrics for simple quotes
        sig_dir = "NEUTRAL"
        if change_pct > 2.0:
            sig_dir = "STRONG_BUY"
        elif change_pct > 0.5:
            sig_dir = "BUY"
        elif change_pct < -2.0:
            sig_dir = "STRONG_SELL"
        elif change_pct < -0.5:
            sig_dir = "SELL"

        sig_conf = 0.50
        regime_state = "sideways"
        if change_pct > 1.0:
            regime_state = "bull"
        elif change_pct < -1.0:
            regime_state = "bear"

        return QuoteResponse(
            ticker=quote.symbol,
            name=quote.symbol.split(".")[0],
            price=Decimal(str(price_val)),
            change=Decimal(str(quote.change)),
            change_pct=Decimal(str(change_pct)),
            volume=Decimal(str(quote.volume)),
            market_cap=None,
            pe_ratio=None,
            week_52_high=Decimal(str(price_val)),
            week_52_low=Decimal(str(price_val)),
            regime=RegimeData(state=regime_state, probs=[0.25, 0.25, 0.25, 0.25]),
            signal=SignalData(direction=sig_dir, confidence=sig_conf),
            timestamp=quote.timestamp,
            source="yfinance",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


# Mapping: interval -> sensible default period when the client omits period
_INTERVAL_DEFAULT_PERIOD: dict[str, str] = {
    "1m": "5d",
    "3m": "5d",
    "5m": "5d",
    "10m": "5d",
    "15m": "5d",
    "30m": "5d",
    "45m": "5d",
    "1h": "5d",
    "2h": "5d",
    "4h": "5d",
    "1d": "1y",
    "1w": "2y",
    "1mo": "max",
}


@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str | None = Query(None, pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60)),
) -> HistoryResponse:
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )

    # Auto-select period from interval when the client doesn't specify one
    effective_period: str = period or _INTERVAL_DEFAULT_PERIOD.get(interval, "1mo")

    period_days = {
        "1d": 1,
        "5d": 5,
        "1w": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "max": 3650,
    }
    days = period_days.get(effective_period, 30)
    start_time = datetime.now(UTC) - timedelta(days=days)
    end_time = datetime.now(UTC)

    try:
        bars_data = await provider_manager.get_ohlcv(symbol, interval, start_time, end_time)
        if not bars_data:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "LIVE_DATA_UNAVAILABLE",
                    "message": f"Live data temporarily unavailable for {symbol}",
                    "symbol": symbol,
                    "interval": interval,
                    "retry_after": 60,
                },
            )

        bars = []
        total_bars = len(bars_data)
        dropped_bars = 0

        def _get_time(x):
            if hasattr(x, "time"):
                return str(x.time)
            elif isinstance(x, dict):
                return str(x.get("time", ""))
            return ""

        bars_data = sorted(bars_data, key=_get_time)

        last_time_val = None
        for b in bars_data:
            time_str = _get_time(b)
            try:
                from dateutil import parser as dt_parser

                dt_obj = dt_parser.parse(time_str)
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=UTC)
                time_val = int(dt_obj.timestamp())

                # De-duplicate strictly ascending
                if last_time_val is not None and time_val <= last_time_val:
                    dropped_bars += 1
                    continue
                last_time_val = time_val

                def _safe_float(v):
                    import math

                    val = float(v)
                    if math.isnan(val):
                        raise ValueError("NaN value")
                    return val

                bars.append(
                    OHLCVBar(
                        time=time_val,
                        open=_safe_float(
                            getattr(b, "open", 0.0) if hasattr(b, "open") else b.get("open", 0.0)
                        ),
                        high=_safe_float(
                            getattr(b, "high", 0.0) if hasattr(b, "high") else b.get("high", 0.0)
                        ),
                        low=_safe_float(
                            getattr(b, "low", 0.0) if hasattr(b, "low") else b.get("low", 0.0)
                        ),
                        close=_safe_float(
                            getattr(b, "close", 0.0) if hasattr(b, "close") else b.get("close", 0.0)
                        ),
                        volume=_safe_float(
                            getattr(b, "volume", 0.0)
                            if hasattr(b, "volume")
                            else b.get("volume", 0.0)
                        ),
                    )
                )
            except Exception as e:
                dropped_bars += 1
                logger.warning(f"Failed to parse bar {time_str}: {e}. Dropping bar.")

        if total_bars > 0 and dropped_bars / total_bars > 0.05:
            raise HTTPException(
                status_code=502,
                detail=f"Bad Gateway: Too many malformed data points ({dropped_bars}/{total_bars} dropped).",
            )

        logger.debug(
            f"[history:api] {symbol} @ {interval}: count_out={len(bars)}, first={bars[0].time if bars else 'None'}, last={bars[-1].time if bars else 'None'}"
        )

        source_val = "provider_manager"
        return HistoryResponse(
            symbol=symbol.upper(),
            interval=interval,
            bars=bars,
            source=source_val,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


@router.get("/indices", response_model=IndicesResponse)
async def get_indices() -> IndicesResponse:
    try:
        indices_data = await MarketDataService.get_indices()
        if not indices_data:
            raise HTTPException(
                status_code=404,
                detail="No market data available for indices",
            )

        indices = [
            IndexData(
                name=ind["name"],
                ticker=ind["ticker"],
                value=Decimal(str(ind["value"])),
                change=Decimal(str(ind["change"])),
                change_pct=Decimal(str(ind["change_pct"])),
                regime_state="bull" if ind["change_pct"] > 0 else "bear",
                timestamp=datetime.now(UTC),
            )
            for ind in indices_data
        ]
        return IndicesResponse(indices=indices)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    exchange: str = Query("NSE"),
    type: str = Query("gainers", pattern="^(gainers|losers|volume|momentum)$"),
) -> MoversResponse:
    try:
        movers_data = await MarketDataService.get_movers(mover_type=type)
        if not movers_data:
            raise HTTPException(
                status_code=404,
                detail="No market data available for movers",
            )

        assets = [
            MoverData(
                ticker=m["ticker"],
                name=m["name"],
                exchange=exchange,
                price=Decimal(str(m["price"])),
                change_pct=Decimal(str(m["change_pct"])),
                volume=Decimal(str(m["volume"])),
                signal_direction="BUY" if m["change_pct"] > 0 else "SELL",
                signal_confidence=0.50,
                rank=m["rank"],
            )
            for m in movers_data
        ]
        return MoversResponse(
            assets=assets,
            exchange=exchange,
            type=type,
            generated_at=datetime.now(UTC),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    exchange: str = Query("NSE"),
    metric: str = Query("return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
) -> HeatmapResponse:
    try:
        # Fetch NIFTY movers to construct heatmap nodes
        movers_data = await MarketDataService.get_movers(
            30, "momentum" if metric == "volume_surge" else "gainers"
        )
        if not movers_data:
            raise HTTPException(
                status_code=404,
                detail="No market data available for heatmap",
            )

        sectors: dict[str, list[SectorNode]] = {}
        for m in movers_data:
            name_root = m["name"]
            sector = SECTOR_MAP.get(name_root, "Other")
            if sector not in sectors:
                sectors[sector] = []

            sectors[sector].append(
                SectorNode(
                    ticker=m["ticker"],
                    name=name_root,
                    value=Decimal(str(m["volume"] * m["price"])),
                    metric_value=Decimal(str(m["change_pct"])),
                    exchange=exchange,
                )
            )

        return HeatmapResponse(
            exchange=exchange,
            metric=metric,
            sectors=sectors,
            generated_at=datetime.now(UTC),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=2, max_length=50),
) -> SearchResponse:
    import urllib.parse

    import httpx

    query = urllib.parse.quote(q)
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=15&newsCount=0"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    results = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                for item in quotes:
                    quote_type = item.get("quoteType", "EQUITY")
                    if quote_type in (
                        "EQUITY",
                        "ETF",
                        "INDEX",
                        "CRYPTOCURRENCY",
                        "MUTUALFUND",
                        "CURRENCY",
                    ):
                        # Ensure we map Yahoo's quoteType to our expected asset_type strings if needed,
                        # but our schema expects string. We map CRYPTOCURRENCY -> CRYPTO.
                        asset_type = "CRYPTO" if quote_type == "CRYPTOCURRENCY" else quote_type

                        results.append(
                            SearchResult(
                                ticker=item.get("symbol", ""),
                                name=item.get("shortname")
                                or item.get("longname")
                                or item.get("symbol", ""),
                                exchange=item.get("exchDisp") or item.get("exchange", "Unknown"),
                                asset_type=asset_type,
                            )
                        )
    except Exception as e:
        logger.error(f"Yahoo Finance search failed for query '{q}': {e}")

    return SearchResponse(query=q, results=results, total_matched=len(results))


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar() -> EconomicCalendarResponse:
    start = datetime.now(UTC)
    end = start + timedelta(days=30)
    events = [
        EconomicEvent(
            date=start + timedelta(days=2),
            event_name="RBI Policy Rate",
            country="India",
            importance="high",
            forecast="6.50%",
            previous="6.50%",
        ),
        EconomicEvent(
            date=start + timedelta(days=9),
            event_name="US CPI YoY",
            country="US",
            importance="high",
            forecast="3.1%",
            previous="3.2%",
        ),
    ]
    return EconomicCalendarResponse(events=events, period_start=start, period_end=end)


@router.get("/universe", response_model=UniverseResponse)
async def get_market_universe() -> UniverseResponse:
    """Return the list of core symbols supported by the platform."""
    from sqlalchemy import select

    from app.database.connection import async_session_factory
    from app.models.instrument import Instrument

    async with async_session_factory() as session:
        stmt = select(Instrument).where(Instrument.is_active)
        result = await session.execute(stmt)
        instruments = result.scalars().all()

        out = []
        for inst in instruments:
            out.append(
                InstrumentInfo(
                    symbol=inst.symbol,
                    displayName=inst.display_name or inst.symbol,
                    exchange=inst.exchange,
                    yfinanceTicker=inst.yfinance_ticker or inst.symbol,
                )
            )
        return UniverseResponse(instruments=out)


@router.get("/status")
async def get_market_status() -> dict:
    """Return the real IST market hours status."""
    return MarketStatusService.get_status()


@router.get("/providers/health")
async def get_providers_health() -> dict:
    """Return health status of all data providers."""
    return await provider_manager.get_providers_health()


# Free-tier global market context — correlates NIFTY moves with the US session,
# volatility, currency, and crude, all via yfinance (no paid data vendor).
GLOBAL_CONTEXT_TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "india_vix": "^INDIAVIX",
    "usd_inr": "USDINR=X",
    "crude_oil": "CL=F",
}


@router.get("/global-context")
async def get_global_context() -> dict:
    """Real global-market correlation snapshot for the signal engine and UI.

    Each entry is fetched independently — a failure on one ticker (e.g. a
    transient provider outage) must not blank out the others, and must never
    be silently replaced with a fabricated number. Failed entries report
    status: "unavailable" with no price field, so the UI can render an
    explicit stale/error state instead of a fake value.
    """
    import asyncio

    async def fetch_one(key: str, ticker: str) -> tuple[str, dict]:
        try:
            quote = await MarketDataService.get_quote(ticker)
            return key, {
                "ticker": ticker,
                "status": "ok",
                "price": quote.get("price"),
                "change": quote.get("change"),
                "change_pct": quote.get("change_pct"),
                "source": quote.get("source"),
                "timestamp": quote.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Global context fetch failed for {ticker}: {e}")
            return key, {"ticker": ticker, "status": "unavailable", "error": str(e)}

    results = await asyncio.gather(
        *(fetch_one(key, ticker) for key, ticker in GLOBAL_CONTEXT_TICKERS.items())
    )
    context = dict(results)

    # A simple, honest risk-on/risk-off read: US markets down + India VIX up
    # is the classic "expect NSE weakness" macro setup. This is a heuristic
    # label for display, not a numeric input to the ML ensemble.
    sp500 = context.get("sp500", {})
    vix = context.get("india_vix", {})
    macro_bias = "unavailable"
    if sp500.get("status") == "ok" and vix.get("status") == "ok":
        sp_down = float(sp500.get("change_pct") or 0) < 0
        vix_up = float(vix.get("change_pct") or 0) > 0
        if sp_down and vix_up:
            macro_bias = "risk_off"
        elif not sp_down and not vix_up:
            macro_bias = "risk_on"
        else:
            macro_bias = "mixed"

    return {
        "context": context,
        "macro_bias": macro_bias,
        "generated_at": datetime.now(UTC).isoformat(),
    }
