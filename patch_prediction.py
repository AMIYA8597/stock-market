import re

with open('backend/app/services/prediction_engine.py', 'r') as f:
    content = f.read()

db_fetch_code_async = '''
    from app.database.connection import async_session_factory
    from sqlalchemy import select
    from app.models.market import Instrument, OHLCV
    
    async with async_session_factory() as session:
        inst = (await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))).scalars().first()
        if not inst:
            bars = []
        else:
            bars = (await session.execute(
                select(OHLCV)
                .where(
                    (OHLCV.instrument_id == inst.id) & 
                    (OHLCV.interval == '1d') & 
                    (OHLCV.timestamp >= start_date) & 
                    (OHLCV.timestamp <= end_date)
                )
                .order_by(OHLCV.timestamp.asc())
            )).scalars().all()
            
    class DummyBar:
        def __init__(self, time, open, high, low, close, volume):
            self.time = time
            self.open = open
            self.high = high
            self.low = low
            self.close = close
            self.volume = volume

    bars = [DummyBar(b.timestamp, float(b.open), float(b.high), float(b.low), float(b.close), float(b.volume)) for b in bars]
'''

# Find the import
content = content.replace('from app.services.data_ingestion.provider_manager import provider_manager', '')
content = re.sub(
    r'bars = await provider_manager\.get_ohlcv\(symbol, "1d", start_date, end_date\)',
    db_fetch_code_async.strip(),
    content
)

with open('backend/app/services/prediction_engine.py', 'w') as f:
    f.write(content)
