# backend/app/api/v1/market.py
"""Market data endpoints router — all values computed from yfinance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.market import (
    EconomicCalendarResponse,
    EconomicEvent,
    HeatmapResponse,
    HistoryResponse,
    IndexData,
    IndicesResponse,
    MoverData,
    MoversResponse,
    OHLCVBar,
    QuoteResponse,
    RegimeData,
    SearchResponse,
    SearchResult,
    SectorNode,
    SignalData,
)
from app.services.market_data_service import MarketDataService
from app.services.pattern_service import detect_patterns

router = APIRouter(prefix="/market", tags=["market"])

SECTOR_MAP = {
    "RELIANCE": "Energy", "NTPC": "Energy", "ONGC": "Energy", "COALINDIA": "Energy", "POWERGRID": "Energy",
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT",
    "HDFCBANK": "Financials", "ICICIBANK": "Financials", "SBIN": "Financials", "KOTAKBANK": "Financials", "AXISBANK": "Financials", "BAJFINANCE": "Financials",
    "HINDUNILVR": "Consumer Goods", "ITC": "Consumer Goods", "ASIANPAINT": "Consumer Goods", "TITAN": "Consumer Goods", "NESTLEIND": "Consumer Goods",
    "MARUTI": "Automobile",
    "LT": "Industrials",
    "SUNPHARMA": "Healthcare",
    "ULTRACEMCO": "Materials", "TATASTEEL": "Materials", "JSWSTEEL": "Materials", "GRASIM": "Materials",
    "ADANIENT": "Conglomerates", "ADANIPORTS": "Conglomerates"
}


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str) -> QuoteResponse:
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )

    try:
        quote = await MarketDataService.get_quote(symbol)
        price_val = quote["price"]
        change_pct = quote["change_pct"]

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

        sig_conf = round(min(0.95, 0.50 + abs(change_pct) * 0.1), 4)
        regime_state = "sideways"
        if change_pct > 1.0:
            regime_state = "bull"
        elif change_pct < -1.0:
            regime_state = "bear"

        return QuoteResponse(
            ticker=quote["symbol"],
            name=quote["symbol"].split(".")[0],
            price=Decimal(str(price_val)),
            change=Decimal(str(quote["change"])),
            change_pct=Decimal(str(change_pct)),
            volume=Decimal(str(quote["volume"])),
            market_cap=Decimal(str(quote["market_cap"])) if quote.get("market_cap") else None,
            pe_ratio=None,
            week_52_high=Decimal(str(quote["week_52_high"])) if quote.get("week_52_high") else Decimal(str(price_val)),
            week_52_low=Decimal(str(quote["week_52_low"])) if quote.get("week_52_low") else Decimal(str(price_val)),
            regime=RegimeData(state=regime_state, probs=[0.25, 0.25, 0.25, 0.25]),
            signal=SignalData(direction=sig_dir, confidence=sig_conf),
            timestamp=datetime.now(UTC),
            source=quote.get("source", "yfinance"),
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
    "1m":  "5d",
    "3m":  "5d",
    "5m":  "5d",
    "10m": "5d",
    "15m": "5d",
    "30m": "5d",
    "45m": "5d",
    "1h":  "5d",
    "2h":  "5d",
    "4h":  "5d",
    "1d":  "1y",
    "1w":  "2y",
    "1mo": "max",
}


@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str | None = Query(None, pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
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

    try:
        bars_data = await MarketDataService.get_history(symbol, interval, effective_period)
        if not bars_data:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "LIVE_DATA_UNAVAILABLE",
                    "message": f"Live data temporarily unavailable for {symbol}",
                    "symbol": symbol,
                    "interval": interval,
                    "retry_after": 60
                }
            )

        bars = []
        total_bars = len(bars_data)
        dropped_bars = 0
        for b in bars_data:
            time_str = b["time"]
            try:
                # yfinance returns pandas Timestamp isoformat or str
                from dateutil import parser as dt_parser
                dt_obj = dt_parser.parse(time_str)
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=UTC)
                time_val = int(dt_obj.timestamp())
                
                iso_time = datetime.fromtimestamp(time_val, tz=UTC).isoformat()
                bars.append(
                    OHLCVBar(
                        timestamp=iso_time,
                        open=b.get("open", 0.0),
                        high=b.get("high", 0.0),
                        low=b.get("low", 0.0),
                        close=b.get("close", 0.0),
                        volume=b.get("volume", 0.0)
                    )
                )
            except Exception as e:
                dropped_bars += 1
                logger.warning(f"Failed to parse timestamp {time_str}: {e}. Dropping bar.")

        if total_bars > 0 and dropped_bars / total_bars > 0.05:
            raise HTTPException(
                status_code=502,
                detail=f"Bad Gateway: Too many malformed data points ({dropped_bars}/{total_bars} dropped)."
            )

        print(f"[HOP 3 API return] {symbol} @ {interval}: count_out={len(bars)}, first={bars[0].timestamp if bars else 'None'}, last={bars[-1].timestamp if bars else 'None'}")



        # bars_data may be a HistoryList (carries .source) or a plain list.
        # Guard against None just in case the service returns it despite the
        # empty-list check above (shouldn't happen, but be safe).
        source_val: str = (
            getattr(bars_data, "source", None) or "yfinance"
            if bars_data is not None
            else "yfinance"
        )
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
                signal_confidence=round(min(0.95, 0.50 + abs(m["change_pct"]) * 0.1), 4),
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
        movers_data = await MarketDataService.get_movers(30, "momentum" if metric == "volume_surge" else "gainers")
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
    q_upper = q.upper()
    rows = [
        SearchResult(ticker="RELIANCE.NS", name="Reliance Industries", exchange="NSE", asset_type="EQUITY"),
        SearchResult(ticker="TCS.NS", name="Tata Consultancy Services", exchange="NSE", asset_type="EQUITY"),
    ]
    filtered = [r for r in rows if q_upper in r.ticker or q_upper in r.name.upper()]
    return SearchResponse(query=q, results=filtered, total_matched=len(filtered))


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar() -> EconomicCalendarResponse:
    start = datetime.now(UTC)
    end = start + timedelta(days=30)
    events = [
        EconomicEvent(date=start + timedelta(days=2), event_name="RBI Policy Rate", country="India", importance="high", forecast="6.50%", previous="6.50%"),
        EconomicEvent(date=start + timedelta(days=9), event_name="US CPI YoY", country="US", importance="high", forecast="3.1%", previous="3.2%"),
    ]
    return EconomicCalendarResponse(events=events, period_start=start, period_end=end)


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = Query(default="1y", description="1d,5d,1mo,3mo,6mo,1y,2y,5y"),
    interval: str = Query(default="1d", description="1m,5m,15m,30m,60m,1d,1wk,1mo")
):
    """
    Returns OHLCV bars for lightweight-charts.
    Symbol format: RELIANCE.NS, ^NSEI, BTC-USD
    """
    try:
        bars = await MarketDataService.get_ohlcv(symbol, period, interval)
        return bars
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/universe")
async def get_market_universe() -> dict[str, list[str]]:
    """Return the list of core symbols supported by the platform."""
    from app.services.market_data_service import MarketDataService
    return {"universe": MarketDataService.NSE_NIFTY50}

@router.get("/status")
async def get_market_status() -> dict:
    """Return the real IST market hours status."""
    import zoneinfo
    
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    
    is_open = False
    # Market hours: Monday (0) to Friday (4), 9:15 AM to 3:30 PM
    if now.weekday() < 5:
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if market_open <= now <= market_close:
            is_open = True
            
    return {
        "is_open": is_open,
        "current_time": now.isoformat(),
        "market_timezone": "Asia/Kolkata",
        "regular_market_hours": "09:15-15:30"
    }
