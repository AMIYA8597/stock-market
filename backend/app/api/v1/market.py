# backend/app/api/v1/market.py
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_rate_limiter
from app.database.connection import get_db
from app.models.market import OHLCV, Exchange, Instrument, InstrumentAlias, QuoteSnapshot
from app.models.regime_states import RegimeState
from app.models.signal import EnsembleSignal
from app.schemas.market import (
    EconomicCalendarResponse,
    HeatmapResponse,
    HistoryResponse,
    IndexData,
    IndicesResponse,
    InstrumentInfo,
    MoverData,
    MoversResponse,
    OHLCVBar,
    QuoteResponse,
    SearchResponse,
    SearchResult,
    SectorNode,
    UniverseResponse,
)
from app.services.market_status import MarketStatusService

_REGIME_LABELS = {0: "sideways", 1: "bull", 2: "bear", 3: "crisis"}


async def _latest_regime_label(db: AsyncSession, instrument_id) -> str:
    """Best-effort regime label from the last computed RegimeState row.

    RegimeState.viterbi_state is a raw HMM state index with no inherent
    semantic meaning; _REGIME_LABELS is a display-only convention for this
    codebase's 4-state model, not a scientifically validated mapping. When no
    regime has been computed for this instrument yet, return "unknown" rather
    than fabricating a state.
    """
    res = await db.execute(
        select(RegimeState.viterbi_state)
        .where(RegimeState.symbol_id == instrument_id)
        .order_by(RegimeState.time.desc())
        .limit(1)
    )
    state = res.scalars().first()
    if state is None:
        return "unknown"
    return _REGIME_LABELS.get(int(state), "unknown")


async def _latest_signal_direction(db: AsyncSession, instrument_id) -> str:
    res = await db.execute(
        select(EnsembleSignal.signal)
        .where(EnsembleSignal.symbol_id == instrument_id)
        .order_by(EnsembleSignal.time.desc())
        .limit(1)
    )
    signal = res.scalars().first()
    if signal is None:
        return "unknown"
    signal = float(signal)
    if signal > 0.1:
        return "bullish"
    if signal < -0.1:
        return "bearish"
    return "neutral"

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
async def get_indices(db: AsyncSession = Depends(get_db)) -> IndicesResponse:
    result = await db.execute(select(Instrument).where(Instrument.asset_class == "INDEX", Instrument.is_active))
    instruments = result.scalars().all()

    indices: list[IndexData] = []
    for inst in instruments:
        q_res = await db.execute(
            select(QuoteSnapshot)
            .where(QuoteSnapshot.instrument_id == inst.id)
            .order_by(QuoteSnapshot.observed_at.desc())
            .limit(1)
        )
        quote = q_res.scalars().first()
        if not quote:
            continue
        indices.append(
            IndexData(
                name=inst.display_name or inst.canonical_symbol,
                ticker=inst.canonical_symbol,
                value=Decimal(str(quote.price or 0)),
                change=Decimal(str(quote.change or 0)),
                change_pct=Decimal(str(quote.change_pct or 0)),
                regime_state=await _latest_regime_label(db, inst.id),
                timestamp=quote.observed_at,
            )
        )
    return IndicesResponse(indices=indices)


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    exchange: str = Query("NSE"),
    type: str = Query("gainers", pattern="^(gainers|losers|volume|momentum)$"),
    db: AsyncSession = Depends(get_db),
) -> MoversResponse:
    exch_res = await db.execute(select(Exchange).where(Exchange.code == exchange))
    exch = exch_res.scalars().first()
    if not exch:
        return MoversResponse(assets=[], exchange=exchange, type=type, generated_at=datetime.now(UTC))

    latest_quote_per_instrument = (
        select(
            QuoteSnapshot.instrument_id,
            QuoteSnapshot.price,
            QuoteSnapshot.change,
            QuoteSnapshot.change_pct,
            QuoteSnapshot.volume,
        )
        .distinct(QuoteSnapshot.instrument_id)
        .order_by(QuoteSnapshot.instrument_id, QuoteSnapshot.observed_at.desc())
        .subquery()
    )

    order_col = {
        "gainers": latest_quote_per_instrument.c.change_pct.desc(),
        "losers": latest_quote_per_instrument.c.change_pct.asc(),
        "volume": latest_quote_per_instrument.c.volume.desc(),
        "momentum": latest_quote_per_instrument.c.change_pct.desc(),
    }[type]

    stmt = (
        select(Instrument, latest_quote_per_instrument)
        .join(latest_quote_per_instrument, latest_quote_per_instrument.c.instrument_id == Instrument.id)
        .where(Instrument.exchange_id == exch.id, Instrument.is_active)
        .order_by(order_col)
        .limit(25)
    )
    rows = (await db.execute(stmt)).all()

    assets = []
    for r in rows:
        inst = r.Instrument
        assets.append(
            MoverData(
                ticker=inst.canonical_symbol,
                name=inst.display_name or inst.canonical_symbol,
                exchange=exchange,
                price=Decimal(str(r.price or 0)),
                change_pct=Decimal(str(r.change_pct or 0)),
                volume=Decimal(str(r.volume or 0)),
                signal_direction=await _latest_signal_direction(db, inst.id),
            )
        )

    return MoversResponse(assets=assets, exchange=exchange, type=type, generated_at=datetime.now(UTC))


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    exchange: str = Query("NSE"),
    metric: str = Query("return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    exch_res = await db.execute(select(Exchange).where(Exchange.code == exchange))
    exch = exch_res.scalars().first()
    if not exch:
        return HeatmapResponse(exchange=exchange, metric=metric, sectors={}, generated_at=datetime.now(UTC))

    result = await db.execute(
        select(Instrument).where(Instrument.exchange_id == exch.id, Instrument.is_active)
    )
    instruments = result.scalars().all()

    sectors: dict[str, list[SectorNode]] = {}
    for inst in instruments:
        q_res = await db.execute(
            select(QuoteSnapshot)
            .where(QuoteSnapshot.instrument_id == inst.id)
            .order_by(QuoteSnapshot.observed_at.desc())
            .limit(1)
        )
        quote = q_res.scalars().first()
        if not quote:
            continue
        # No GICS-style sector classification is stored on Instrument yet; group
        # by market_segment (a real, non-fabricated field) rather than inventing
        # sector names.
        segment = inst.market_segment or "UNCLASSIFIED"
        metric_value = quote.change_pct if metric != "volume_surge" else quote.volume
        sectors.setdefault(segment, []).append(
            SectorNode(
                ticker=inst.canonical_symbol,
                name=inst.display_name or inst.canonical_symbol,
                value=Decimal(str(quote.price or 0)),
                metric_value=Decimal(str(metric_value or 0)),
            )
        )

    return HeatmapResponse(exchange=exchange, metric=metric, sectors=sectors, generated_at=datetime.now(UTC))


@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=2, max_length=50),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    pattern = f"%{q.strip()}%"
    result = await db.execute(
        select(Instrument)
        .where(
            Instrument.is_active,
            (Instrument.canonical_symbol.ilike(pattern)) | (Instrument.display_name.ilike(pattern)),
        )
        .limit(20)
    )
    instruments = result.scalars().all()

    results = []
    for inst in instruments:
        exch_res = await db.execute(select(Exchange).where(Exchange.id == inst.exchange_id))
        exch = exch_res.scalars().first()
        results.append(
            SearchResult(
                ticker=inst.canonical_symbol,
                name=inst.display_name or inst.canonical_symbol,
                exchange=exch.code if exch else "UNKNOWN",
                asset_type=inst.asset_class or "EQUITY",
            )
        )

    return SearchResponse(query=q, results=results, total_matched=len(results))


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar() -> EconomicCalendarResponse:
    # No economic-calendar ingestion pipeline exists in this codebase yet
    # (macro/economic event data is not part of the canonical data platform).
    # Returning an honest empty result rather than fabricating events.
    now = datetime.now(UTC)
    return EconomicCalendarResponse(events=[], period_start=now, period_end=now + timedelta(days=7))


@router.get("/universe", response_model=UniverseResponse)
async def get_market_universe(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> UniverseResponse:
    result = await db.execute(
        select(Instrument)
        .where(Instrument.is_active, Instrument.is_tradable)
        .order_by(Instrument.canonical_symbol.asc())
        .offset(offset)
        .limit(limit)
    )
    instruments = result.scalars().all()

    infos = []
    for inst in instruments:
        exch_res = await db.execute(select(Exchange).where(Exchange.id == inst.exchange_id))
        exch = exch_res.scalars().first()
        alias_res = await db.execute(
            select(InstrumentAlias).where(
                InstrumentAlias.instrument_id == inst.id, InstrumentAlias.provider == "yfinance"
            )
        )
        alias = alias_res.scalars().first()
        infos.append(
            InstrumentInfo(
                symbol=inst.canonical_symbol,
                displayName=inst.display_name or inst.canonical_symbol,
                exchange=exch.code if exch else "UNKNOWN",
                yfinanceTicker=alias.provider_symbol if alias else inst.canonical_symbol,
            )
        )

    return UniverseResponse(instruments=infos, limit=limit, offset=offset)


@router.get("/status")
async def get_market_status() -> dict:
    return MarketStatusService.get_status()


@router.get("/providers/health")
async def get_providers_health() -> dict:
    from app.services.ingestion.provider_manager import provider_manager

    return await provider_manager.get_providers_health()


@router.get("/global-context")
async def get_global_context(db: AsyncSession = Depends(get_db)) -> dict:
    """Cross-market context (global indices, VIX, FX) for the terminal's macro widget.

    No global-index ingestion pipeline exists in this codebase yet, so this
    returns an explicit unavailable status rather than fabricating index levels.
    """
    result = await db.execute(select(Instrument).where(Instrument.asset_class == "INDEX", Instrument.is_active))
    instruments = result.scalars().all()
    if not instruments:
        return {
            "status": "unavailable",
            "message": "No global index instruments are configured in the canonical data platform yet.",
            "indices": [],
        }

    context = []
    for inst in instruments:
        q_res = await db.execute(
            select(QuoteSnapshot)
            .where(QuoteSnapshot.instrument_id == inst.id)
            .order_by(QuoteSnapshot.observed_at.desc())
            .limit(1)
        )
        quote = q_res.scalars().first()
        if quote:
            context.append(
                {
                    "ticker": inst.canonical_symbol,
                    "name": inst.display_name or inst.canonical_symbol,
                    "value": float(quote.price or 0),
                    "change_pct": float(quote.change_pct or 0),
                    "as_of": quote.observed_at.isoformat(),
                }
            )
    return {"status": "ok" if context else "unavailable", "indices": context}  # honesty: allow (conditional on real fetched quotes above)
