import re

with open('backend/app/services/alert_engine.py', 'r') as f:
    content = f.read()

# Replace _get_signal_for_alert to use DB
new_get_signal = '''async def _get_signal_for_alert(symbol: str) -> dict:
    from app.database.connection import async_session_factory
    from sqlalchemy import select
    from app.models.market import Instrument, OHLCV
    
    async with async_session_factory() as session:
        inst_res = await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        inst = inst_res.scalars().first()
        if not inst:
            raise ValueError(f"No history available for {symbol}")
            
        ohlcv_res = await session.execute(
            select(OHLCV)
            .where((OHLCV.instrument_id == inst.id) & (OHLCV.interval == '1d'))
            .order_by(OHLCV.timestamp.asc())
        )
        bars = ohlcv_res.scalars().all()
        
        if not bars:
            raise ValueError(f"No history available for {symbol}")
            
        hist = []
        for b in bars:
            hist.append({
                'time': b.timestamp.timestamp(),
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': float(b.volume)
            })

    df = pd.DataFrame(hist)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])

    res = TechnicalSignalEngine.generate_signal(df)
    res["current_price"] = df.iloc[-1]["close"]
    return res'''

content = re.sub(
    r'async def _get_signal_for_alert\(symbol: str\) -> dict:.*?return res',
    new_get_signal,
    content,
    flags=re.DOTALL
)
content = content.replace('from app.services.market_data_service import MarketDataService', '')

with open('backend/app/services/alert_engine.py', 'w') as f:
    f.write(content)
