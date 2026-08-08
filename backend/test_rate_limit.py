import asyncio
import time

from app.services.market_data_service import MarketDataService


async def main():
    # Generate 50 symbols
    symbols = [MarketDataService.NSE_NIFTY50[i % len(MarketDataService.NSE_NIFTY50)] for i in range(50)]

    print(f"Fetching {len(symbols)} symbols...")
    start_time = time.time()

    results = await MarketDataService.get_batch_quotes(symbols)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"Elapsed time: {elapsed:.2f} seconds")
    print(f"Rate: {len(symbols) / elapsed:.2f} symbols / second")
    if elapsed >= 5.0:
        print("Rate limiting is enforced.")
    else:
        print("WARNING: Rate limiting might not be enforced.")

if __name__ == "__main__":
    asyncio.run(main())
