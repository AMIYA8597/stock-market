import re

with open('backend/app/services/prediction_engine.py', 'r') as f:
    content = f.read()

# I will find the badly indented block and replace it.
pattern = r"from app\.database\.connection import async_session_factory.*?bars = \[DummyBar.*?\]"

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

content = re.sub(pattern, db_fetch_code_async.strip('\n'), content, flags=re.DOTALL)

with open('backend/app/services/prediction_engine.py', 'w') as f:
    f.write(content)
