import re

with open('backend/app/tasks/backtest_tasks.py', 'r') as f:
    content = f.read()

# Replace MarketDataService import
content = content.replace('from app.services.market_data_service import MarketDataService', 
                          '''from sqlalchemy import select
from app.models.market import Instrument, OHLCV''')

# Replace the history fetching block
fetch_code = '''
            # 2. Fetch history from DB
            symbol = job.universe[0]
            import pandas as pd
            
            inst_res = await db.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
            inst = inst_res.scalars().first()
            if not inst:
                df = pd.DataFrame()
            else:
                ohlcv_res = await db.execute(
                    select(OHLCV)
                    .where((OHLCV.instrument_id == inst.id) & (OHLCV.interval == '1d'))
                    .order_by(OHLCV.timestamp.asc())
                )
                bars = ohlcv_res.scalars().all()
                if not bars:
                    df = pd.DataFrame()
                else:
                    df = pd.DataFrame([{
                        'time': b.timestamp,
                        'open': float(b.open),
                        'high': float(b.high),
                        'low': float(b.low),
                        'close': float(b.close),
                        'volume': float(b.volume)
                    } for b in bars])

'''

pattern = r"# 2\. Fetch history[\s\S]*?df = pd\.DataFrame\(history_data\)"

content = re.sub(pattern, fetch_code.strip(), content)

with open('backend/app/tasks/backtest_tasks.py', 'w') as f:
    f.write(content)
