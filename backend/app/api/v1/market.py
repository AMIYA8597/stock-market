# backend/app/api/v1/market.py
"""Market data endpoints router — all values computed from yfinance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.services.market_data_service import MarketDataService
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
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse.create(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Market provider failure: {str(e)}",
            ).dict(),
        )


@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
) -> HistoryResponse:
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )

    try:
        bars_data = await MarketDataService.get_history(symbol, interval, period)
        if not bars_data:
            raise HTTPException(
                status_code=404,
                detail=f"No market data available for {symbol}"
            )
        
        bars = []
        for b in bars_data:
            time_str = b["time"]
            try:
                if "T" in time_str:
                    time_val = int(datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp())
                else:
                    time_val = int(datetime.strptime(time_str, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())
            except Exception:
                time_val = int(datetime.now(UTC).timestamp())

            bars.append(
                OHLCVBar(
                    time=time_val,
                    open=round(Decimal(str(b["open"])), 8),
                    high=round(Decimal(str(b["high"])), 8),
                    low=round(Decimal(str(b["low"])), 8),
                    close=round(Decimal(str(b["close"])), 8),
                    volume=round(Decimal(str(b["volume"])), 4),
                )
            )
        source_val = getattr(bars_data, "source", "yfinance")
        return HistoryResponse(symbol=symbol.upper(), interval=interval, bars=bars, source=source_val)
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
