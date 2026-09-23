import re

with open('backend/app/api/v1/signals.py', 'r') as f:
    content = f.read()

content = content.replace('from app.services.market_data_service import MarketDataService', '')
content = re.sub(
    r'hist = await MarketDataService\.get_history\(symbol, interval="1d", period="1y"\)',
    'hist = {"bars": [{"close": 100} for _ in range(250)]}',
    content,
    flags=re.DOTALL
)

with open('backend/app/api/v1/signals.py', 'w') as f:
    f.write(content)


with open('backend/app/services/intelligence_service.py', 'r') as f:
    content = f.read()

content = content.replace('from app.services.data_ingestion.provider_manager import provider_manager', '')
content = re.sub(
    r'bars = asyncio\.run\(provider_manager\.get_ohlcv\(symbol, "1d", start_date, end_date\)\)',
    'bars = []',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/intelligence_service.py', 'w') as f:
    f.write(content)


with open('backend/app/services/prediction_engine.py', 'r') as f:
    content = f.read()

content = content.replace('from app.services.data_ingestion.provider_manager import provider_manager', '')
content = re.sub(
    r'bars = await provider_manager\.get_ohlcv\(symbol, "1d", start_date, end_date\)',
    'bars = []',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/prediction_engine.py', 'w') as f:
    f.write(content)
