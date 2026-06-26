import os
import sys
import asyncio

# Add backend directory to PYTHONPATH
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.market_data_service import MarketDataService

async def main():
    quote = await MarketDataService.get_quote('AAPL')
    print('Quote:', quote)
    history = await MarketDataService.get_history('AAPL', '1d', '1mo')
    print('History rows:', len(history))

if __name__ == '__main__':
    asyncio.run(main())
