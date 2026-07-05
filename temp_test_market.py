import os
import sys
import asyncio
import traceback

# Add backend directory to PYTHONPATH
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.market_data_service import MarketDataService

async def main():
    print("Testing MARUTI.NS Quote...")
    try:
        quote = await MarketDataService.get_quote('MARUTI.NS')
        print('Quote succeeded:', quote)
    except Exception as e:
        print('Quote failed:')
        traceback.print_exc()

    print("\nTesting MARUTI.NS History...")
    try:
        history = await MarketDataService.get_history('MARUTI.NS', '1d', '3mo')
        print(f'History succeeded: {len(history)} bars')
        if history:
            print("First bar:", history[0])
            print("Last bar:", history[-1])
            print("Source:", getattr(history, "source", "N/A"))
    except Exception as e:
        print('History failed:')
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())



