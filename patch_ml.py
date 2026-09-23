import re

db_fetch_code = '''
            # Synchronous fetch from DB
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import sessionmaker
            from app.models.market import Instrument, OHLCV
            from app.core.config import get_settings
            
            settings = get_settings()
            # Must use a sync engine for synchronous methods
            sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
            engine = create_engine(sync_url)
            SessionLocal = sessionmaker(bind=engine)
            
            with SessionLocal() as session:
                inst = session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol)).scalars().first()
                if not inst:
                    bars = []
                else:
                    bars = session.execute(
                        select(OHLCV)
                        .where(
                            (OHLCV.instrument_id == inst.id) & 
                            (OHLCV.interval == '1d') & 
                            (OHLCV.timestamp >= start_date) & 
                            (OHLCV.timestamp <= end_date)
                        )
                        .order_by(OHLCV.timestamp.asc())
                    ).scalars().all()
                    
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

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Find the block in intelligence_service
    # We replace from "from app.services.data_ingestion.provider_manager" to "else: ... asyncio.run(...)"
    
    # Actually, we can just replace the whole fetching logic.
    if "provider_manager" in content:
        pattern = r"from app\.services\.data_ingestion\.provider_manager import provider_manager[\s\S]*?bars = asyncio\.run\(provider_manager\.get_ohlcv\(symbol, \"1d\", start_date, end_date\)\)"
        content = re.sub(pattern, db_fetch_code.strip(), content)
        
        with open(filepath, 'w') as f:
            f.write(content)

patch_file('backend/app/services/intelligence_service.py')
patch_file('backend/app/services/prediction_engine.py')
