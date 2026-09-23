import os

file_path = 'backend/app/api/v1/market.py'
with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('@router.get("/quote/{symbol}", response_model=QuoteResponse)'):
        new_lines.append("""@router.get("/quotes/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
) -> QuoteResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    from sqlalchemy import select
    from app.models.market import Instrument, QuoteSnapshot
    import math

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

    sig_dir = "NEUTRAL"
    if change_pct > 2.0: sig_dir = "STRONG_BUY"
    elif change_pct > 0.5: sig_dir = "BUY"
    elif change_pct < -2.0: sig_dir = "STRONG_SELL"
    elif change_pct < -0.5: sig_dir = "SELL"

    regime_state = "sideways"
    if change_pct > 1.0: regime_state = "bull"
    elif change_pct < -1.0: regime_state = "bear"

    return QuoteResponse(
        ticker=symbol,
        name=instrument.display_name or symbol,
        price=Decimal(str(price_val)),
        change=Decimal(str(quote.change or 0.0)),
        change_pct=Decimal(str(change_pct)),
        volume=Decimal(str(quote.volume or 0.0)),
        market_cap=None,
        pe_ratio=None,
        week_52_high=Decimal(str(price_val)),
        week_52_low=Decimal(str(price_val)),
        regime=RegimeData(state=regime_state, probs=[0.25, 0.25, 0.25, 0.25]),
        signal=SignalData(direction=sig_dir, confidence=0.50),
        timestamp=quote.observed_at,
        source="canonical_db",
    )
""")
        skip = True
        continue
    
    if skip and line.startswith('@router.get("/history/{symbol}"'):
        skip = False

    if not skip:
        new_lines.append(line)

lines = new_lines
new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('@router.get("/history/{symbol}", response_model=HistoryResponse)'):
        new_lines.append("""@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$"),
    period: str | None = Query(None, pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60)),
) -> HistoryResponse:
    if not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required.")

    from sqlalchemy import select
    from app.models.market import Instrument, OHLCV

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
""")
        skip = True
        continue
    
    if skip and line.startswith('@router.get("/indices"'):
        skip = False

    if not skip:
        new_lines.append(line)


with open(file_path, 'w') as f:
    f.writelines(new_lines)

