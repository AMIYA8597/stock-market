import re

def fix_signals():
    with open('backend/app/api/v1/signals.py', 'r') as f:
        content = f.read()

    # Remove MarketDataService
    content = content.replace('from app.services.market_data_service import MarketDataService', 
                              'from app.database.connection import get_db\nfrom sqlalchemy import select\nfrom app.models.market import OHLCV, Instrument\nfrom sqlalchemy.ext.asyncio import AsyncSession')
    
    # We need to pass db to get_signals maybe? Wait, get_signals doesn't have db.
    # Let's check get_signals signature in signals.py
    print("Will need manual review of signals.py")

fix_signals()
