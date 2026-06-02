"""Market data endpoints router (GET /market/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
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


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str, db: AsyncSession = Depends(get_db)) -> QuoteResponse:
    _ = db
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="symbol is required.",
            ).dict(),
        )

    return QuoteResponse(
        ticker=symbol.upper(),
        name=f"{symbol.upper()} LTD",
        price=Decimal("2521.30000000"),
        change=Decimal("33.80000000"),
        change_pct=Decimal("1.3600"),
        volume=Decimal("1823400.0000"),
        market_cap=Decimal("1720000000000.00"),
        pe_ratio=Decimal("24.1200"),
        week_52_high=Decimal("3018.00000000"),
        week_52_low=Decimal("2121.10000000"),
        regime=RegimeData(state="bull", probs=[0.61, 0.13, 0.21, 0.05]),
        signal=SignalData(direction="BUY", confidence=0.73),
        timestamp=datetime.now(UTC),
    )


@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|5m|15m|1h|1d)$"),
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    _ = db
    _ = period
    now = datetime.now(UTC)
    rows = []
    for i in range(30):
        t = now - timedelta(days=(29 - i))
        base = Decimal("2500") + Decimal(i)
        rows.append(
            OHLCVBar(
                time=t,
                open=base,
                high=base + Decimal("12.2"),
                low=base - Decimal("9.7"),
                close=base + Decimal("4.3"),
                volume=Decimal("1000000") + Decimal(i * 10000),
            )
        )
    return HistoryResponse(symbol=symbol.upper(), interval=interval, data=rows)


@router.get("/indices", response_model=IndicesResponse)
async def get_indices(db: AsyncSession = Depends(get_db)) -> IndicesResponse:
    _ = db
    now = datetime.now(UTC)
    return IndicesResponse(
        indices=[
            IndexData(name="NIFTY 50", ticker="^NSEI", value=Decimal("22430.22000000"), change=Decimal("180.42000000"), change_pct=Decimal("0.8100"), regime_state="bull", timestamp=now),
            IndexData(name="S&P 500", ticker="^GSPC", value=Decimal("6120.51000000"), change=Decimal("21.33000000"), change_pct=Decimal("0.3500"), regime_state="sideways", timestamp=now),
        ]
    )


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    exchange: str = Query("NSE"),
    type: str = Query("gainers", pattern="^(gainers|losers|volume|momentum)$"),
    db: AsyncSession = Depends(get_db),
) -> MoversResponse:
    _ = db
    assets = [
        MoverData(
            ticker="RELIANCE.NS",
            name="Reliance Industries",
            exchange=exchange,
            price=Decimal("2521.30000000"),
            change_pct=Decimal("1.3600"),
            volume=Decimal("1823400.0000"),
            signal_direction="BUY",
            signal_confidence=0.73,
            rank=1,
        ),
        MoverData(
            ticker="TCS.NS",
            name="TCS",
            exchange=exchange,
            price=Decimal("4242.70000000"),
            change_pct=Decimal("0.9400"),
            volume=Decimal("721400.0000"),
            signal_direction="BUY",
            signal_confidence=0.69,
            rank=2,
        ),
    ]
    return MoversResponse(assets=assets, exchange=exchange, type=type, generated_at=datetime.now(UTC))


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    exchange: str = Query("NSE"),
    metric: str = Query("return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    _ = db
    sectors = {
        "Energy": [
            SectorNode(ticker="RELIANCE.NS", name="Reliance", value=Decimal("1240.20"), metric_value=Decimal("1.36"), exchange=exchange)
        ],
        "IT": [
            SectorNode(ticker="TCS.NS", name="TCS", value=Decimal("920.11"), metric_value=Decimal("0.94"), exchange=exchange)
        ],
    }
    return HeatmapResponse(exchange=exchange, metric=metric, sectors=sectors, generated_at=datetime.now(UTC))


@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=2, max_length=50),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    _ = db
    q_upper = q.upper()
    rows = [
        SearchResult(ticker="RELIANCE.NS", name="Reliance Industries", exchange="NSE", asset_type="EQUITY"),
        SearchResult(ticker="TCS.NS", name="Tata Consultancy Services", exchange="NSE", asset_type="EQUITY"),
    ]
    filtered = [r for r in rows if q_upper in r.ticker or q_upper in r.name.upper()]
    return SearchResponse(query=q, results=filtered, total_matched=len(filtered))


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar(db: AsyncSession = Depends(get_db)) -> EconomicCalendarResponse:
    _ = db
    start = datetime.now(UTC)
    end = start + timedelta(days=30)
    events = [
        EconomicEvent(date=start + timedelta(days=2), event_name="RBI Policy Rate", country="India", importance="high", forecast="6.50%", previous="6.50%"),
        EconomicEvent(date=start + timedelta(days=9), event_name="US CPI YoY", country="US", importance="high", forecast="3.1%", previous="3.2%"),
    ]
    return EconomicCalendarResponse(events=events, period_start=start, period_end=end)
