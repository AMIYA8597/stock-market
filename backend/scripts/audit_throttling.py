import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.market_data_service import MarketDataService

# Let's take the first 100 NIFTY 50 + other NSE stocks or just generate some dummy NSE symbols
TEST_SYMBOLS = MarketDataService.NSE_NIFTY50 + [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBI.NS", "LICI.NS", "ITC.NS", "HUL.NS", "BHARTIARTL.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS", "SUNPHARMA.NS",
    "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "NTPC.NS", "POWERGRID.NS",
    "TATASTEEL.NS", "ONGC.NS", "COALINDIA.NS", "M&M.NS", "JSWSTEEL.NS",
    "GRASIM.NS", "ADANIPORTS.NS", "TECHM.NS", "DRREDDY.NS", "CIPLA.NS",
    "DIVISLAB.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "TATACONSUM.NS", "HEROMOTOCO.NS",
    "EICHERMOT.NS", "BPCL.NS", "SHREECEM.NS", "INDUSINDBK.NS", "UPL.NS",
    "HINDALCO.NS", "SBILIFE.NS", "HDFCLIFE.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"
] * 4  # Repeat to get ~250 items

async def main():
    print(f"Starting audit with {len(TEST_SYMBOLS)} symbols")
    start_time = time.time()

    # We will use get_batch_quotes which concurrently hits get_quote for all symbols
    results = await MarketDataService.get_batch_quotes(TEST_SYMBOLS)

    end_time = time.time()

    success = 0
    failures = 0
    latency = end_time - start_time

    for _sym, res in results.items():
        if res and res.get("price") is not None:
            success += 1
        else:
            failures += 1

    print("\n--- AUDIT RESULTS ---")
    print(f"Total Requests: {len(TEST_SYMBOLS)}")
    print(f"Success: {success}")
    print(f"Failures: {failures}")
    print(f"Failure Rate: {(failures/len(TEST_SYMBOLS))*100:.2f}%")
    print(f"Total Time: {latency:.2f} seconds")
    print(f"Throughput: {len(TEST_SYMBOLS)/latency:.2f} requests/sec")

if __name__ == "__main__":
    asyncio.run(main())
