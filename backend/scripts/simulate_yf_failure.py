import asyncio
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Mock yfinance to fail
import yfinance as yf

from app.services.market_data_service import MarketDataService


def fake_ticker(*args, **kwargs):
    raise Exception("Simulated yfinance timeout or rate limit")
yf.Ticker = fake_ticker

async def test_fallback():
    symbol = "RELIANCE.NS"
    print(f"Testing fallback for {symbol} with yfinance mocked to fail...")
    try:
        quote = await MarketDataService.get_quote(symbol)
        print("Quote Result:", json.dumps(quote, indent=2))

        # Verify source is present and not yfinance
        assert "source" in quote, "Source field is missing!"
        assert quote["source"] != "yfinance", "Source should not be yfinance!"
        print(f"Success! Fallback engaged properly. Source: {quote['source']}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_fallback())
