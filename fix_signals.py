import re

with open('backend/app/api/v1/signals.py', 'r') as f:
    content = f.read()

content = content.replace('from app.services.market_data_service import MarketDataService', 
                          '''from app.database.connection import async_session_factory
from sqlalchemy import select
from app.models.market import Instrument, OHLCV''')

# Replace _get_technical_signal implementation
new_get_signal = '''async def _get_technical_signal(symbol: str) -> dict:
    async with async_session_factory() as session:
        # Find instrument
        inst_res = await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        inst = inst_res.scalars().first()
        if not inst:
            raise ValueError(f"No history available for {symbol}")
        
        # Get OHLCV
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
    # convert cols to numeric
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])

    return TechnicalSignalEngine.generate_signal(df)'''

content = re.sub(
    r'async def _get_technical_signal\(symbol: str\) -> dict:.*?return TechnicalSignalEngine\.generate_signal\(df\)',
    new_get_signal,
    content,
    flags=re.DOTALL
)

with open('backend/app/api/v1/signals.py', 'w') as f:
    f.write(content)
