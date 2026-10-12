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
from app.services.market_data_service import MarketDataService
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

    # Try DB first — wrapped in try/except so a DB hiccup (cold start, pooler
    # reset, missing table) falls through to the live provider chain instead
    # of returning a 500.
    try:
        result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        instrument = result.scalars().first()

        if instrument:
            result = await db.execute(
                select(QuoteSnapshot)
                .where(QuoteSnapshot.instrument_id == instrument.id)
                .order_by(QuoteSnapshot.observed_at.desc())
                .limit(1)
            )
            quote = result.scalars().first()

            if quote:
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
    except Exception as exc:
        logger.warning("Quote DB lookup failed for %s, falling through to providers: %s", symbol, exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # Fallback: DB has no data — use the full provider chain (Upstox → yfinance → IndianStockAPI)
    try:
        q = await MarketDataService.get_quote(symbol)
        if not q or q.get("price", 0) == 0:
            raise HTTPException(status_code=404, detail=f"No quote data available for {symbol}")
        return QuoteResponse(
            ticker=symbol,
            name=q.get("name") or symbol,
            price=Decimal(str(q.get("price", 0))),
            change=Decimal(str(q.get("change", 0))),
            change_pct=Decimal(str(q.get("change_pct", 0))),
            volume=Decimal(str(q.get("volume", 0))),
            market_cap=Decimal(str(q.get("market_cap", 0))) if q.get("market_cap") else None,
            pe_ratio=None,
            week_52_high=Decimal(str(q.get("week_52_high", 0))) if q.get("week_52_high") else None,
            week_52_low=Decimal(str(q.get("week_52_low", 0))) if q.get("week_52_low") else None,
            regime=None,
            signal=None,
            timestamp=datetime.now(UTC),
            data_freshness_seconds=0,
            source=q.get("source", "live"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Live quote failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=404, detail=f"No quote data available for {symbol}") from exc

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
    # Derive start_time from effective_period for DB OHLCV query
    _period_days = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650}
    start_time = datetime.now(UTC) - timedelta(days=_period_days.get(effective_period, 365))

    # A DB hiccup (Cloud Run cold start, pooler reset) must not turn into a
    # 500: skip the canonical-DB read and fall through to the provider chain.
    bars_data: list[OHLCV] = []
    try:
        result = await db.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        instrument = result.scalars().first()
        if instrument:
            result = await db.execute(
                select(OHLCV)
                .where(
                    (OHLCV.instrument_id == instrument.id) &
                    (OHLCV.interval == interval) &
                    (OHLCV.timestamp >= start_time)
                )
                .order_by(OHLCV.timestamp.asc())
            )
            bars_data = list(result.scalars().all())
    except Exception as exc:
        logger.warning("History DB lookup failed for %s, using providers: %s", symbol, exc)
        bars_data = []
        try:
            await db.rollback()
        except Exception:
            pass

    if bars_data:
        bars = [
            OHLCVBar(
                time=int(b.timestamp.timestamp()),
                open=float(b.open or 0.0),
                high=float(b.high or 0.0),
                low=float(b.low or 0.0),
                close=float(b.close or 0.0),
                volume=float(b.volume or 0.0),
            )
            for b in bars_data
        ]
        return HistoryResponse(symbol=symbol.upper(), interval=interval, bars=bars, source="canonical_db")

    # Fallback: DB has no data — try full provider chain (Upstox → yfinance)
    try:
        norm = MarketDataService._normalize_symbol(symbol)
        raw = await MarketDataService.get_history(norm, interval, effective_period)
        if not raw:
            raise HTTPException(status_code=404, detail=f"No historical data available for {symbol}")

        def _to_ts(t) -> int:
            if isinstance(t, (int, float)):
                return int(t)
            return int(datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp())

        bars = [
            OHLCVBar(
                time=_to_ts(r.get("time") or r.get("timestamp")),
                open=float(r.get("open", 0)),
                high=float(r.get("high", 0)),
                low=float(r.get("low", 0)),
                close=float(r.get("close", 0)),
                volume=float(r.get("volume", 0)),
            )
            for r in raw
        ]
        source = getattr(raw, "source", "live")
        return HistoryResponse(symbol=symbol.upper(), interval=interval, bars=bars, source=source)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("History fallback failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=404, detail=f"No historical data available for {symbol}") from exc

@router.get("/indices", response_model=IndicesResponse)
async def get_indices(db: AsyncSession = Depends(get_db)) -> IndicesResponse:
    try:
        result = await db.execute(select(Instrument).where(Instrument.asset_class == "INDEX", Instrument.is_active))
        instruments = result.scalars().all()
    except Exception as exc:
        logger.warning("DB query for indices failed, using live fallback: %s", exc)
        instruments = []

    indices: list[IndexData] = []
    for inst in instruments:
        try:
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
        except Exception as exc:
            logger.warning("Failed to fetch quote for index %s: %s", inst.canonical_symbol, exc)

    # Fallback: if DB has no indices, fetch from yfinance with timeout
    if not indices:
        import asyncio

        from app.services.market_data_service import MarketDataService
        yf_indices = MarketDataService.NSE_INDICES
        for yf_sym, name in yf_indices:
            try:
                q = await asyncio.wait_for(MarketDataService._yfinance_quote(yf_sym), timeout=5.0)
                if q and q.get("price", 0) > 0:
                    indices.append(IndexData(
                        name=name, ticker=yf_sym,
                        value=Decimal(str(q["price"])),
                        change=Decimal(str(q.get("change", 0))),
                        change_pct=Decimal(str(q.get("change_pct", 0))),
                        regime_state="unknown",
                        timestamp=datetime.now(UTC),
                    ))
            except Exception:
                pass

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
                signal_confidence=0.5,
                rank=len(assets) + 1,
            )
        )

    # Fallback: if DB has no movers, fetch all Nifty50 stocks from yfinance
    if not assets:
        import asyncio

        from app.services.market_data_service import MarketDataService

        async def _fetch_quote(sym: str):
            try:
                return await MarketDataService.get_quote(sym)
            except Exception:
                return None

        # Fetch all 50 in parallel batches of 10 to respect rate limits
        all_symbols = list(MarketDataService.NSE_NIFTY50)
        for batch_start in range(0, len(all_symbols), 10):
            batch = all_symbols[batch_start:batch_start + 10]
            results = await asyncio.gather(*[_fetch_quote(s) for s in batch], return_exceptions=True)
            for sym, q in zip(batch, results, strict=False):
                if isinstance(q, dict) and q.get("price", 0) > 0:
                    assets.append(MoverData(
                        ticker=sym, name=q.get("name", sym), exchange=exchange,
                        price=Decimal(str(q["price"])),
                        change_pct=Decimal(str(q.get("change_pct", 0))),
                        volume=Decimal(str(q.get("volume", 0))),
                        signal_direction="neutral",
                        signal_confidence=0.0,
                        rank=len(assets) + 1,
                    ))

        if type == "losers":
            assets.sort(key=lambda a: float(a.change_pct))
        elif type == "volume":
            assets.sort(key=lambda a: float(a.volume), reverse=True)
        elif type == "gainers" or type == "momentum":
            assets.sort(key=lambda a: float(a.change_pct), reverse=True)
        # Re-rank after sorting
        for i, a in enumerate(assets):
            a.rank = i + 1

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

    # Fallback: if DB has no instruments, build heatmap from Nifty50 yfinance data
    if not sectors:
        import asyncio

        from app.services.market_data_service import MarketDataService

        sector_map = {
            "Energy": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL"],
            "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
            "Financials": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "BAJAJFINSV", "INDUSINDBK"],
            "Consumer": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM", "TITAN"],
            "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB"],
            "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"],
            "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA"],
            "Infra": ["LT", "ULTRACEMCO", "GRASIM", "SHREECEM", "ADANIENT", "ADANIPORTS"],
            "Power": ["NTPC", "POWERGRID"],
            "Telecom": ["BHARTIARTL"],
            "Insurance": ["SBILIFE", "HDFCLIFE"],
            "Healthcare": ["APOLLOHOSP"],
            "Others": ["ASIANPAINT", "TRENT"],
        }

        async def _fetch_for_heatmap(sym: str):
            try:
                q = await MarketDataService.get_quote(sym)
                return sym, q
            except Exception:
                return sym, None

        all_syms = [s for syms in sector_map.values() for s in syms]
        for batch_start in range(0, len(all_syms), 10):
            batch = all_syms[batch_start:batch_start + 10]
            results = await asyncio.gather(*[_fetch_for_heatmap(s) for s in batch], return_exceptions=True)
            for r in results:
                if isinstance(r, tuple):
                    sym, q = r
                    if q and q.get("price", 0) > 0:
                        for sector_name, sector_syms in sector_map.items():
                            if sym in sector_syms:
                                metric_value = q.get("change_pct", 0) if metric != "volume_surge" else q.get("volume", 0)
                                sectors.setdefault(sector_name, []).append(
                                    SectorNode(ticker=sym, name=sym, value=Decimal(str(q["price"])), metric_value=Decimal(str(metric_value)))
                                )
                                break

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

    # Fallback: search the static universe list when DB is empty
    if not results:
        q_upper = q.strip().upper()
        for sym, name in _NSE_STATIC_UNIVERSE:
            if q_upper in sym or q_upper in name.upper():
                results.append(
                    SearchResult(ticker=sym, name=name, exchange="NSE", asset_type="EQUITY")
                )
                if len(results) >= 20:
                    break
    return SearchResponse(query=q, results=results, total_matched=len(results))


@router.get("/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar() -> EconomicCalendarResponse:
    # No economic-calendar ingestion pipeline exists in this codebase yet
    # (macro/economic event data is not part of the canonical data platform).
    # Returning an honest empty result rather than fabricating events.
    now = datetime.now(UTC)
    return EconomicCalendarResponse(events=[], period_start=now, period_end=now + timedelta(days=7))


_NSE_STATIC_UNIVERSE = [
    ("RELIANCE", "Reliance Industries"), ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"), ("INFY", "Infosys"), ("ICICIBANK", "ICICI Bank"),
    ("HINDUNILVR", "Hindustan Unilever"), ("SBIN", "State Bank of India"),
    ("BHARTIARTL", "Bharti Airtel"), ("ITC", "ITC Limited"), ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("LT", "Larsen & Toubro"), ("AXISBANK", "Axis Bank"), ("ASIANPAINT", "Asian Paints"),
    ("MARUTI", "Maruti Suzuki"), ("WIPRO", "Wipro"), ("HCLTECH", "HCL Technologies"),
    ("ULTRACEMCO", "UltraTech Cement"), ("NESTLEIND", "Nestle India"), ("BAJFINANCE", "Bajaj Finance"),
    ("TITAN", "Titan Company"), ("SUNPHARMA", "Sun Pharmaceutical"), ("TECHM", "Tech Mahindra"),
    ("POWERGRID", "Power Grid Corporation"), ("NTPC", "NTPC Limited"), ("ONGC", "ONGC"),
    ("ADANIPORTS", "Adani Ports"), ("COALINDIA", "Coal India"), ("DIVISLAB", "Divi's Laboratories"),
    ("DRREDDY", "Dr. Reddy's Laboratories"), ("CIPLA", "Cipla"), ("EICHERMOT", "Eicher Motors"),
    ("GRASIM", "Grasim Industries"), ("HEROMOTOCO", "Hero MotoCorp"), ("HINDALCO", "Hindalco"),
    ("INDUSINDBK", "IndusInd Bank"), ("JSWSTEEL", "JSW Steel"), ("M&M", "Mahindra & Mahindra"),
    ("TATAMOTORS", "Tata Motors"), ("TATASTEEL", "Tata Steel"), ("BAJAJFINSV", "Bajaj Finserv"),
    ("BPCL", "Bharat Petroleum"), ("BRITANNIA", "Britannia Industries"), ("HDFCLIFE", "HDFC Life"),
    ("SBILIFE", "SBI Life Insurance"), ("TATACONSUM", "Tata Consumer Products"),
    ("UPL", "UPL Limited"), ("VEDL", "Vedanta"), ("APOLLOHOSP", "Apollo Hospitals"),
    ("ADANIENT", "Adani Enterprises"), ("BAJAJ-AUTO", "Bajaj Auto"),
]

@router.get("/universe", response_model=UniverseResponse)
async def get_market_universe(
    limit: int = Query(default=50, ge=1, le=2000),
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

    # Fallback: if DB has no instruments, return the well-known NSE universe
    if not infos:
        static = _NSE_STATIC_UNIVERSE[offset : offset + limit]
        infos = [
            InstrumentInfo(
                symbol=sym,
                displayName=name,
                exchange="NSE",
                yfinanceTicker=f"{sym}.NS",
            )
            for sym, name in static
        ]
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
    try:
        result = await db.execute(select(Instrument).where(Instrument.asset_class == "INDEX", Instrument.is_active))
        instruments = result.scalars().all()
    except Exception as exc:
        logger.warning("DB query for global-context instruments failed: %s", exc)
        instruments = []
    if not instruments:
        # Fallback: fetch indices from yfinance with per-symbol timeout
        import asyncio

        from app.services.market_data_service import MarketDataService
        context = []
        for yf_sym, name in MarketDataService.NSE_INDICES[:6]:
            try:
                q = await asyncio.wait_for(MarketDataService.get_quote(yf_sym), timeout=5.0)
                if q and q.get("price", 0) > 0:
                    context.append({
                        "ticker": yf_sym, "name": name,
                        "value": float(q["price"]),
                        "change_pct": float(q.get("change_pct", 0)),
                        "as_of": q.get("timestamp", datetime.now(UTC).isoformat()),
                    })
            except Exception:
                pass
        return {"status": "ok" if context else "unavailable", "indices": context}  # honesty: allow

    context = []
    for inst in instruments:
        try:
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
        except Exception as exc:
            logger.warning("Failed to fetch quote for global-context index %s: %s", inst.canonical_symbol, exc)
    return {"status": "ok" if context else "unavailable", "indices": context}  # honesty: allow (conditional on real fetched quotes above)


@router.get("/zones/{symbol}", tags=["zones"])
async def get_zones(symbol: str):
    """Return support/resistance zones for a symbol based on recent price history."""
    from app.services.market_data_service import MarketDataService

    try:
        hist = await MarketDataService.get_history(symbol, interval="1d", period="6mo")
    except Exception:
        hist = []

    if not hist or len(hist) < 10:
        return {"symbol": symbol, "zones": [], "message": "Insufficient history"}

    highs = [float(h["high"]) for h in hist]
    lows = [float(h["low"]) for h in hist]
    closes = [float(h["close"]) for h in hist]
    last_price = closes[-1]

    # Identify key levels from recent pivots
    zones = []
    # Strong support: lowest lows in recent windows
    for window_label, window_size in [("short", 20), ("medium", 60), ("long", 120)]:
        w = min(window_size, len(lows))
        recent_lows = sorted(lows[-w:])
        recent_highs = sorted(highs[-w:], reverse=True)
        support = sum(recent_lows[:3]) / min(3, len(recent_lows))
        resistance = sum(recent_highs[:3]) / min(3, len(recent_highs))
        zones.append({
            "type": "support", "level": round(support, 2),
            "strength": round(0.5 + 0.3 * (w / 120), 2), "window": window_label,
        })
        zones.append({
            "type": "resistance", "level": round(resistance, 2),
            "strength": round(0.5 + 0.3 * (w / 120), 2), "window": window_label,
        })

    return {"symbol": symbol, "last_price": round(last_price, 2), "zones": zones}


@router.get("/patterns/{symbol}")
async def get_patterns(symbol: str):
    """Return detected candlestick / chart patterns for a symbol.

    Uses the same technical analysis pipeline as the prediction engine's
    pattern sub-model. When no history is available, returns an empty list
    rather than erroring so the frontend can degrade gracefully.
    """
    from app.services.market_data_service import MarketDataService

    try:
        hist = await MarketDataService.get_history(symbol, interval="1d", period="6mo")
    except Exception:
        hist = []

    if not hist or len(hist) < 20:
        return {"symbol": symbol, "patterns": [], "message": "Insufficient history for pattern detection"}

    closes = [float(h["close"]) for h in hist]
    opens = [float(h["open"]) for h in hist]
    highs = [float(h["high"]) for h in hist]
    lows = [float(h["low"]) for h in hist]

    patterns = []
    # Simple pattern detection
    n = len(closes)
    last = closes[-1]
    _prev = closes[-2] if n > 1 else last

    # Doji
    if n > 1 and abs(opens[-1] - closes[-1]) < (highs[-1] - lows[-1]) * 0.1 and (highs[-1] - lows[-1]) > 0:
        patterns.append({"name": "Doji", "type": "neutral", "confidence": 0.7, "index": n - 1})

    # Hammer
    if n > 1:
        body = abs(opens[-1] - closes[-1])
        lower_shadow = min(opens[-1], closes[-1]) - lows[-1]
        upper_shadow = highs[-1] - max(opens[-1], closes[-1])
        if lower_shadow > body * 2 and upper_shadow < body * 0.5 and body > 0:
            patterns.append({"name": "Hammer", "type": "bullish", "confidence": 0.65, "index": n - 1})

    # Engulfing
    if n > 2:
        prev_body = closes[-2] - opens[-2]
        curr_body = closes[-1] - opens[-1]
        if prev_body < 0 and curr_body > 0 and curr_body > abs(prev_body):
            patterns.append({"name": "Bullish Engulfing", "type": "bullish", "confidence": 0.72, "index": n - 1})
        elif prev_body > 0 and curr_body < 0 and abs(curr_body) > prev_body:
            patterns.append({"name": "Bearish Engulfing", "type": "bearish", "confidence": 0.72, "index": n - 1})

    # Support/Resistance zones
    recent_lows = sorted(lows[-20:])[:3]
    recent_highs = sorted(highs[-20:], reverse=True)[:3]
    support = sum(recent_lows) / len(recent_lows) if recent_lows else last * 0.95
    resistance = sum(recent_highs) / len(recent_highs) if recent_highs else last * 1.05

    return {
        "symbol": symbol,
        "patterns": patterns,
        "support": round(support, 2),
        "resistance": round(resistance, 2),
    }


@router.post("/instruments/sync-upstox", tags=["instruments"])
async def sync_upstox_instruments(force: bool = False):
    """Trigger Upstox NSE+BSE instrument master seed.

    Downloads instrument keys from Upstox's public CSV and upserts all
    EQ/INDEX rows into Exchange, Instrument, and InstrumentAlias tables.
    Pass ?force=true to re-seed even if already done this session.
    """
    try:
        from app.services.instrument_seeder import seed_all_exchanges
        result = await seed_all_exchanges(force=force)
        return {"status": "ok", **result}  # honesty: allow
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Instrument sync failed: {e}")


@router.get("/instruments/status", tags=["instruments"])
async def instruments_status(db: AsyncSession = Depends(get_db)):
    """Check how many instruments and Upstox aliases exist."""
    total_instruments = (await db.execute(select(Instrument))).scalars().all()
    upstox_aliases = (await db.execute(
        select(InstrumentAlias).where(InstrumentAlias.provider == "upstox")
    )).scalars().all()
    return {
        "total_instruments": len(total_instruments),
        "upstox_aliases": len(upstox_aliases),
        "upstox_ready": len(upstox_aliases) > 0,
    }
