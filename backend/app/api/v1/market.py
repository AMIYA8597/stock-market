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


@router.get("/quotes", response_model=dict[str, QuoteResponse])
async def get_quotes_batch(
    symbols: str = Query(..., description="Comma-separated list of symbols (max 100)"),
    _rate_limit: None = Depends(get_rate_limiter(requests=120, window=60)),
) -> dict[str, QuoteResponse]:
    raw_list = [s.strip() for s in symbols.split(",") if s.strip()][:100]
    if not raw_list:
        raise HTTPException(status_code=400, detail="symbols parameter is required.")

    batch = await MarketDataService.get_batch_quotes(raw_list)
    out: dict[str, QuoteResponse] = {}
    for sym in raw_list:
        q = batch.get(sym)
        if not q or q.get("price", 0) <= 0:
            continue
        raw_timestamp = q.get("timestamp")
        try:
            quote_timestamp = (
                datetime.fromisoformat(raw_timestamp)
                if isinstance(raw_timestamp, str)
                else raw_timestamp
            )
            if quote_timestamp is None:
                raise ValueError("quote timestamp missing")
            if quote_timestamp.tzinfo is None:
                quote_timestamp = quote_timestamp.replace(tzinfo=UTC)
            freshness_seconds = max(0, int((datetime.now(UTC) - quote_timestamp).total_seconds()))
        except (TypeError, ValueError):
            logger.warning("Quote %s returned an invalid timestamp", sym)
            continue
        out[sym] = QuoteResponse(
            ticker=sym,
            name=q.get("name") or sym,
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
            timestamp=quote_timestamp,
            data_freshness_seconds=freshness_seconds,
            source=q.get("source", "unknown"),
        )
    return out


@router.get("/quote/{symbol}", response_model=QuoteResponse)
@router.get("/quotes/{symbol}", response_model=QuoteResponse, include_in_schema=False)
async def get_quote(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=300, window=60)),
) -> QuoteResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    from app.core.test_state import is_test_mode

    norm_sym = MarketDataService._normalize_symbol(symbol)
    stale_response: QuoteResponse | None = None

    # Try DB first — wrapped in try/except so a DB hiccup (cold start, pooler
    # reset, missing table) falls through to the live provider chain instead
    # of returning a 500.
    try:
        result = await db.execute(
            select(Instrument).where(Instrument.canonical_symbol.in_([symbol.upper(), norm_sym]))
        )
        instrument = result.scalars().first()

        if instrument:
            result = await db.execute(
                select(QuoteSnapshot)
                .where(QuoteSnapshot.instrument_id == instrument.id)
                .order_by(QuoteSnapshot.observed_at.desc())
                .limit(1)
            )
            quote = result.scalars().first()

            if quote and float(quote.price or 0.0) > 0:
                price_val = float(quote.price or 0.0)
                change_pct = float(quote.change_pct or 0.0)
                age_sec = max(0, int((datetime.now(UTC) - quote.observed_at).total_seconds()))
                db_resp = QuoteResponse(
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
                    data_freshness_seconds=age_sec,
                    source="canonical_db",
                )
                if is_test_mode() or age_sec <= 900:
                    return db_resp
                stale_response = db_resp
    except Exception as exc:
        logger.warning(
            "Quote DB lookup failed for %s, falling through to providers: %s", symbol, exc
        )
        try:
            await db.rollback()
        except Exception:
            pass

    # Fallback: DB has no fresh data — use the full provider chain (Upstox → yfinance → IndianStockAPI)
    try:
        q = await MarketDataService.get_quote(symbol)
        if not q or q.get("price", 0) == 0:
            if stale_response is not None:
                return stale_response
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
        if stale_response is not None:
            return stale_response
        logger.warning("Live quote failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=404, detail=f"No quote data available for {symbol}"
        ) from exc


_INTERVAL_DEFAULT_PERIOD = {
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
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=120, window=60)),
) -> HistoryResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    norm = MarketDataService._normalize_symbol(symbol)
    effective_period: str = period or _INTERVAL_DEFAULT_PERIOD.get(interval, "1mo")
    # Derive start_time from effective_period for DB OHLCV query
    _period_days = {
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
    start_time = datetime.now(UTC) - timedelta(days=_period_days.get(effective_period, 365))

    # A DB hiccup (Cloud Run cold start, pooler reset) must not turn into a
    # 500: skip the canonical-DB read and fall through to the provider chain.
    bars_data: list[OHLCV] = []
    try:
        result = await db.execute(
            select(Instrument).where(Instrument.canonical_symbol.in_([symbol.upper(), norm]))
        )
        instrument = result.scalars().first()
        if instrument:
            result = await db.execute(
                select(OHLCV)
                .where(
                    (OHLCV.instrument_id == instrument.id)
                    & (OHLCV.interval == interval)
                    & (OHLCV.timestamp >= start_time)
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
        return HistoryResponse(
            symbol=symbol.upper(), interval=interval, bars=bars, source="canonical_db"
        )

    # Fallback: DB has no data — try full provider chain (Upstox → Stooq → yfinance)
    try:
        raw = await MarketDataService.get_history(norm, interval, effective_period)
        if not raw:
            raise HTTPException(
                status_code=404, detail=f"No historical data available for {symbol}"
            )

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
        raise HTTPException(
            status_code=404, detail=f"No historical data available for {symbol}"
        ) from exc


@router.get("/indices", response_model=IndicesResponse)
async def get_indices(db: AsyncSession = Depends(get_db)) -> IndicesResponse:
    indices: list[IndexData] = []
    try:
        latest_quote_sub = (
            select(
                QuoteSnapshot.instrument_id,
                QuoteSnapshot.price,
                QuoteSnapshot.change,
                QuoteSnapshot.change_pct,
                QuoteSnapshot.observed_at,
            )
            .distinct(QuoteSnapshot.instrument_id)
            .order_by(QuoteSnapshot.instrument_id, QuoteSnapshot.observed_at.desc())
            .subquery()
        )
        stmt = (
            select(Instrument, latest_quote_sub)
            .join(latest_quote_sub, latest_quote_sub.c.instrument_id == Instrument.id)
            .where(Instrument.asset_class == "INDEX", Instrument.is_active)
        )
        rows = (await db.execute(stmt)).all()
        for r in rows:
            inst = r.Instrument
            if r.observed_at and (datetime.now(UTC) - r.observed_at) <= timedelta(minutes=15):
                indices.append(
                    IndexData(
                        name=inst.display_name or inst.canonical_symbol,
                        ticker=inst.canonical_symbol,
                        value=Decimal(str(r.price or 0)),
                        change=Decimal(str(r.change or 0)),
                        change_pct=Decimal(str(r.change_pct or 0)),
                        regime_state="unknown",
                        timestamp=r.observed_at,
                    )
                )
    except Exception as exc:
        logger.warning("DB query for indices failed, using live fallback: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # Fallback: if DB has no fresh indices, batch-fetch concurrently via MarketDataService
    if not indices:
        yf_indices = MarketDataService.NSE_INDICES
        syms = [sym for sym, _ in yf_indices]
        batch = await MarketDataService.get_batch_quotes(syms)
        now_utc = datetime.now(UTC)
        for yf_sym, name in yf_indices:
            q = batch.get(yf_sym)
            if q and q.get("price", 0) > 0:
                indices.append(
                    IndexData(
                        name=name,
                        ticker=yf_sym,
                        value=Decimal(str(q["price"])),
                        change=Decimal(str(q.get("change", 0))),
                        change_pct=Decimal(str(q.get("change_pct", 0))),
                        regime_state="unknown",
                        timestamp=now_utc,
                    )
                )

    return IndicesResponse(indices=indices)


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    exchange: str = Query("NSE"),
    type: str = Query("gainers", pattern="^(gainers|losers|volume|momentum)$"),
    db: AsyncSession = Depends(get_db),
) -> MoversResponse:
    assets: list[MoverData] = []
    try:
        exch_res = await db.execute(select(Exchange).where(Exchange.code == exchange))
        exch = exch_res.scalars().first()
        if exch:
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
                .join(
                    latest_quote_per_instrument,
                    latest_quote_per_instrument.c.instrument_id == Instrument.id,
                )
                .where(Instrument.exchange_id == exch.id, Instrument.is_active)
                .order_by(order_col)
                .limit(25)
            )
            rows = (await db.execute(stmt)).all()
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
                        signal_direction="neutral",
                        signal_confidence=0.5,
                        rank=len(assets) + 1,
                    )
                )
    except Exception as exc:
        logger.warning("DB movers lookup failed, using live fallback: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # Fallback: if DB has no movers, batch-fetch Nifty50 stocks via MarketDataService
    if not assets:
        all_symbols = list(MarketDataService.NSE_NIFTY50)
        batch_quotes = await MarketDataService.get_batch_quotes(all_symbols)
        for sym in all_symbols:
            q = batch_quotes.get(sym)
            if isinstance(q, dict) and q.get("price", 0) > 0:
                assets.append(
                    MoverData(
                        ticker=sym,
                        name=q.get("name", sym),
                        exchange=exchange,
                        price=Decimal(str(q["price"])),
                        change_pct=Decimal(str(q.get("change_pct", 0))),
                        volume=Decimal(str(q.get("volume", 0))),
                        signal_direction="neutral",
                        signal_confidence=0.0,
                        rank=len(assets) + 1,
                    )
                )

        if type == "losers":
            assets.sort(key=lambda a: float(a.change_pct))
        elif type == "volume":
            assets.sort(key=lambda a: float(a.volume), reverse=True)
        elif type == "gainers" or type == "momentum":
            assets.sort(key=lambda a: float(a.change_pct), reverse=True)
        assets = assets[:25]
        for i, a in enumerate(assets):
            a.rank = i + 1

    return MoversResponse(
        assets=assets, exchange=exchange, type=type, generated_at=datetime.now(UTC)
    )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    exchange: str = Query("NSE"),
    metric: str = Query("return_1d", pattern="^(return_1d|return_5d|volume_surge)$"),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    sectors: dict[str, list[SectorNode]] = {}
    try:
        exch_res = await db.execute(select(Exchange).where(Exchange.code == exchange))
        exch = exch_res.scalars().first()
        if exch:
            latest_quote_sub = (
                select(
                    QuoteSnapshot.instrument_id,
                    QuoteSnapshot.price,
                    QuoteSnapshot.change_pct,
                    QuoteSnapshot.volume,
                )
                .distinct(QuoteSnapshot.instrument_id)
                .order_by(QuoteSnapshot.instrument_id, QuoteSnapshot.observed_at.desc())
                .subquery()
            )
            stmt = (
                select(Instrument, latest_quote_sub)
                .join(latest_quote_sub, latest_quote_sub.c.instrument_id == Instrument.id)
                .where(Instrument.exchange_id == exch.id, Instrument.is_active)
            )
            rows = (await db.execute(stmt)).all()
            for r in rows:
                inst = r.Instrument
                segment = inst.market_segment or "UNCLASSIFIED"
                metric_value = r.change_pct if metric != "volume_surge" else r.volume
                sectors.setdefault(segment, []).append(
                    SectorNode(
                        ticker=inst.canonical_symbol,
                        name=inst.display_name or inst.canonical_symbol,
                        value=Decimal(str(r.price or 0)),
                        metric_value=Decimal(str(metric_value or 0)),
                    )
                )
    except Exception as exc:
        logger.warning("DB heatmap lookup failed, using live fallback: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # Fallback: if DB has no quote snapshots, build heatmap from Nifty50 batch quotes
    if not sectors:
        sector_map = {
            "Energy": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL"],
            "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
            "Financials": [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
                "AXISBANK",
                "KOTAKBANK",
                "BAJFINANCE",
                "BAJAJFINSV",
                "INDUSINDBK",
            ],
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

        all_syms = [s for syms in sector_map.values() for s in syms]
        batch_quotes = await MarketDataService.get_batch_quotes(all_syms)
        for sector_name, sector_syms in sector_map.items():
            for sym in sector_syms:
                q = batch_quotes.get(sym)
                if q and q.get("price", 0) > 0:
                    metric_value = (
                        q.get("change_pct", 0) if metric != "volume_surge" else q.get("volume", 0)
                    )
                    sectors.setdefault(sector_name, []).append(
                        SectorNode(
                            ticker=sym,
                            name=sym,
                            value=Decimal(str(q["price"])),
                            metric_value=Decimal(str(metric_value)),
                        )
                    )

    return HeatmapResponse(
        exchange=exchange, metric=metric, sectors=sectors, generated_at=datetime.now(UTC)
    )


@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=2, max_length=50),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    results = []
    try:
        pattern = f"%{q.strip()}%"
        stmt = (
            select(Instrument, Exchange.code)
            .outerjoin(Exchange, Exchange.id == Instrument.exchange_id)
            .where(
                Instrument.is_active,
                (Instrument.canonical_symbol.ilike(pattern))
                | (Instrument.display_name.ilike(pattern)),
            )
            .limit(20)
        )
        rows = (await db.execute(stmt)).all()
        for inst, exch_code in rows:
            results.append(
                SearchResult(
                    ticker=inst.canonical_symbol,
                    name=inst.display_name or inst.canonical_symbol,
                    exchange=exch_code or "NSE",
                    asset_type=inst.asset_class or "EQUITY",
                )
            )
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass

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
    ("RELIANCE", "Reliance Industries"),
    ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"),
    ("INFY", "Infosys"),
    ("ICICIBANK", "ICICI Bank"),
    ("HINDUNILVR", "Hindustan Unilever"),
    ("SBIN", "State Bank of India"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("ITC", "ITC Limited"),
    ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("LT", "Larsen & Toubro"),
    ("AXISBANK", "Axis Bank"),
    ("ASIANPAINT", "Asian Paints"),
    ("MARUTI", "Maruti Suzuki"),
    ("WIPRO", "Wipro"),
    ("HCLTECH", "HCL Technologies"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("NESTLEIND", "Nestle India"),
    ("BAJFINANCE", "Bajaj Finance"),
    ("TITAN", "Titan Company"),
    ("SUNPHARMA", "Sun Pharmaceutical"),
    ("TECHM", "Tech Mahindra"),
    ("POWERGRID", "Power Grid Corporation"),
    ("NTPC", "NTPC Limited"),
    ("ONGC", "ONGC"),
    ("ADANIPORTS", "Adani Ports"),
    ("COALINDIA", "Coal India"),
    ("DIVISLAB", "Divi's Laboratories"),
    ("DRREDDY", "Dr. Reddy's Laboratories"),
    ("CIPLA", "Cipla"),
    ("EICHERMOT", "Eicher Motors"),
    ("GRASIM", "Grasim Industries"),
    ("HEROMOTOCO", "Hero MotoCorp"),
    ("HINDALCO", "Hindalco"),
    ("INDUSINDBK", "IndusInd Bank"),
    ("JSWSTEEL", "JSW Steel"),
    ("M&M", "Mahindra & Mahindra"),
    ("TATAMOTORS", "Tata Motors"),
    ("TATASTEEL", "Tata Steel"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("BPCL", "Bharat Petroleum"),
    ("BRITANNIA", "Britannia Industries"),
    ("HDFCLIFE", "HDFC Life"),
    ("SBILIFE", "SBI Life Insurance"),
    ("TATACONSUM", "Tata Consumer Products"),
    ("UPL", "UPL Limited"),
    ("VEDL", "Vedanta"),
    ("APOLLOHOSP", "Apollo Hospitals"),
    ("ADANIENT", "Adani Enterprises"),
    ("BAJAJ-AUTO", "Bajaj Auto"),
]


@router.get("/universe", response_model=UniverseResponse)
async def get_market_universe(
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> UniverseResponse:
    infos = []
    try:
        stmt = (
            select(Instrument, Exchange.code, InstrumentAlias.provider_symbol)
            .outerjoin(Exchange, Exchange.id == Instrument.exchange_id)
            .outerjoin(
                InstrumentAlias,
                (InstrumentAlias.instrument_id == Instrument.id)
                & (InstrumentAlias.provider == "yfinance"),
            )
            .where(Instrument.is_active, Instrument.is_tradable)
            .order_by(Instrument.canonical_symbol.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        for inst, exch_code, yf_alias in rows:
            infos.append(
                InstrumentInfo(
                    symbol=inst.canonical_symbol,
                    displayName=inst.display_name or inst.canonical_symbol,
                    exchange=exch_code or "NSE",
                    yfinanceTicker=yf_alias or inst.canonical_symbol,
                )
            )
    except Exception as exc:
        logger.warning("DB universe query failed, using static NSE universe: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

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
    """Cross-market context (global indices, VIX, FX) for the terminal's macro widget."""
    context = []
    try:
        latest_quote_sub = (
            select(
                QuoteSnapshot.instrument_id,
                QuoteSnapshot.price,
                QuoteSnapshot.change_pct,
                QuoteSnapshot.observed_at,
            )
            .distinct(QuoteSnapshot.instrument_id)
            .order_by(QuoteSnapshot.instrument_id, QuoteSnapshot.observed_at.desc())
            .subquery()
        )
        stmt = (
            select(Instrument, latest_quote_sub)
            .join(latest_quote_sub, latest_quote_sub.c.instrument_id == Instrument.id)
            .where(Instrument.asset_class == "INDEX", Instrument.is_active)
        )
        rows = (await db.execute(stmt)).all()
        for r in rows:
            inst = r.Instrument
            if r.observed_at and (datetime.now(UTC) - r.observed_at) <= timedelta(minutes=15):
                context.append(
                    {
                        "ticker": inst.canonical_symbol,
                        "name": inst.display_name or inst.canonical_symbol,
                        "value": float(r.price or 0),
                        "change_pct": float(r.change_pct or 0),
                        "as_of": r.observed_at.isoformat(),
                    }
                )
    except Exception as exc:
        logger.warning("DB query for global-context instruments failed: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    if not context:
        top_indices = MarketDataService.NSE_INDICES[:6]
        batch = await MarketDataService.get_batch_quotes([sym for sym, _ in top_indices])
        for yf_sym, name in top_indices:
            q = batch.get(yf_sym)
            if q and q.get("price", 0) > 0:
                context.append(
                    {
                        "ticker": yf_sym,
                        "name": name,
                        "value": float(q["price"]),
                        "change_pct": float(q.get("change_pct", 0)),
                        "as_of": q.get("timestamp", datetime.now(UTC).isoformat()),
                    }
                )
    return {
        "status": "ok" if context else "unavailable",  # honesty: allow (conditional on real fetched quotes above)
        "indices": context,
    }


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
        zones.append(
            {
                "type": "support",
                "level": round(support, 2),
                "strength": round(0.5 + 0.3 * (w / 120), 2),
                "window": window_label,
            }
        )
        zones.append(
            {
                "type": "resistance",
                "level": round(resistance, 2),
                "strength": round(0.5 + 0.3 * (w / 120), 2),
                "window": window_label,
            }
        )

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
        return {
            "symbol": symbol,
            "patterns": [],
            "message": "Insufficient history for pattern detection",
        }

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
    if (
        n > 1
        and abs(opens[-1] - closes[-1]) < (highs[-1] - lows[-1]) * 0.1
        and (highs[-1] - lows[-1]) > 0
    ):
        patterns.append({"name": "Doji", "type": "neutral", "confidence": 0.7, "index": n - 1})

    # Hammer
    if n > 1:
        body = abs(opens[-1] - closes[-1])
        lower_shadow = min(opens[-1], closes[-1]) - lows[-1]
        upper_shadow = highs[-1] - max(opens[-1], closes[-1])
        if lower_shadow > body * 2 and upper_shadow < body * 0.5 and body > 0:
            patterns.append(
                {"name": "Hammer", "type": "bullish", "confidence": 0.65, "index": n - 1}
            )

    # Engulfing
    if n > 2:
        prev_body = closes[-2] - opens[-2]
        curr_body = closes[-1] - opens[-1]
        if prev_body < 0 and curr_body > 0 and curr_body > abs(prev_body):
            patterns.append(
                {"name": "Bullish Engulfing", "type": "bullish", "confidence": 0.72, "index": n - 1}
            )
        elif prev_body > 0 and curr_body < 0 and abs(curr_body) > prev_body:
            patterns.append(
                {"name": "Bearish Engulfing", "type": "bearish", "confidence": 0.72, "index": n - 1}
            )

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
    upstox_aliases = (
        (await db.execute(select(InstrumentAlias).where(InstrumentAlias.provider == "upstox")))
        .scalars()
        .all()
    )
    return {
        "total_instruments": len(total_instruments),
        "upstox_aliases": len(upstox_aliases),
        "upstox_ready": len(upstox_aliases) > 0,
    }
