# backend/app/api/v1/market.py
from __future__ import annotations
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_rate_limiter
from app.database.connection import get_db
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
from app.models.market import Instrument, QuoteSnapshot, OHLCV
from app.services.market_status import MarketStatusService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/quote/{symbol}", response_model=QuoteResponse)
@router.get("/quotes/{symbol}", response_model=QuoteResponse, include_in_schema=False)
async def get_quote(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
) -> QuoteResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
    instrument = result.scalars().first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    result = await db.execute(
        select(QuoteSnapshot)
        .where(QuoteSnapshot.instrument_id == instrument.id)
        .order_by(QuoteSnapshot.observed_at.desc())
        .limit(1)
    )
    quote = result.scalars().first()
    
    if not quote:
        raise HTTPException(status_code=404, detail=f"No quotes available for {symbol}")

    price_val = float(quote.price or 0.0)
    change_pct = float(quote.change_pct or 0.0)

    return QuoteResponse(
        ticker=symbol,
        name=instrument.display_name or symbol,
        price=Decimal(str(price_val)),
        change=Decimal(str(quote.change or 0.0)),
        change_pct=Decimal(str(change_pct)),
        volume=Decimal(str(quote.volume or 0.0)),
        market_cap=None,
        pe_ratio=None,
        week_52_high=None,
        week_52_low=None,
        regime=None,
        signal=None,
        timestamp=quote.observed_at,
        data_freshness_seconds=max(0, int((datetime.now(UTC) - quote.observed_at).total_seconds())),
        source="canonical_db",
    )


_INTERVAL_DEFAULT_PERIOD = {
    "1m": "5d", "3m": "5d", "5m": "5d", "10m": "5d", "15m": "5d", "30m": "5d", "45m": "5d",
    "1h": "5d", "2h": "5d", "4h": "5d", "1d": "1y", "1w": "2y", "1mo": "max",
}

@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str | None = Query(None, pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60)),
) -> HistoryResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    effective_period: str = period or _INTERVAL_DEFAULT_PERIOD.get(interval, "1mo")
    period_days = {"1d": 1, "5d": 5, "1w": 7, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650}
    days = period_days.get(effective_period, 30)
    start_time = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
    instrument = result.scalars().first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

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

    if not bars_data:
        raise HTTPException(status_code=404, detail=f"No historical data for {symbol}")

    bars = []
    for b in bars_data:
        bars.append(
            OHLCVBar(
                time=int(b.timestamp.timestamp()),
                open=float(b.open or 0.0),
                high=float(b.high or 0.0),
                low=float(b.low or 0.0),
                close=float(b.close or 0.0),
                volume=float(b.volume or 0.0)
            )
        )

    return HistoryResponse(
        symbol=symbol.upper(),
        interval=interval,
        bars=bars,
        source="canonical_db",
    )


@router.get("/indices", response_model=IndicesResponse)
async def get_indices() -> IndicesResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    exchange: str = Query("NSE"),
    type: str = Query("gainers", pattern="^(gainers|losers|volume|momentum)$"),
) -> MoversResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    exchange: str = Query("NSE"),
    metric: str = Query("return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
) -> HeatmapResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=2, max_length=50),
) -> SearchResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar() -> EconomicCalendarResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/universe", response_model=UniverseResponse)
async def get_market_universe() -> UniverseResponse:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}


@router.get("/status")
async def get_market_status() -> dict:
    return MarketStatusService.get_status()


@router.get("/providers/health")
async def get_providers_health() -> dict:
    return {"status": "running", "message": "Migrated to Canonical DB"}


@router.get("/global-context")
async def get_global_context() -> dict:
    return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}