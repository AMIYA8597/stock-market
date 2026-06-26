import asyncio
from app.services.market_data_service import MarketDataService

async def main():
    quote = await MarketDataService.get_quote('AAPL')
    print('Quote:', quote)
    hist = await MarketDataService.get_history('AAPL', '1d', '5d')
    print('History length:', len(hist))

if __name__ == '__main__':
    asyncio.run(main())
