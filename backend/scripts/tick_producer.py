"""Live Tick Producer Broadcaster — Background loop polling prices and publishing to Redis."""

import sys
import pathlib
import asyncio
import json
import logging
from datetime import datetime, UTC
import yfinance as yf

# Add backend directory to path
project_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.database.redis_client import get_redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

async def main():
    logger.info("Starting live tick producer broadcaster...")
    
    try:
        redis = await get_redis()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    last_prices = {}
    
    # Initialize with current prices
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            price = getattr(ticker.fast_info, "last_price", None)
            if price is not None:
                last_prices[symbol] = float(price)
                logger.info(f"Initial price for {symbol}: {price}")
        except Exception as e:
            logger.warning(f"Could not get initial price for {symbol}: {e}")

    logger.info("Starting polling loop (every 15 seconds)...")
    while True:
        for symbol in SYMBOLS:
            try:
                # Fetch fresh last price
                ticker = yf.Ticker(symbol)
                price = getattr(ticker.fast_info, "last_price", None)
                
                if price is not None:
                    price_val = float(price)
                    old_price = last_prices.get(symbol)
                    
                    if old_price is None or price_val != old_price:
                        last_prices[symbol] = price_val
                        payload = {
                            "symbol": symbol.upper(),
                            "price": price_val,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "channel": "signals.updates"
                        }
                        # Publish price updates to Redis channel
                        await redis.publish("signals.updates", json.dumps(payload))
                        logger.info(f"Broadcast update: {symbol} -> {price_val}")
            except Exception as e:
                logger.error(f"Error checking tick for {symbol}: {e}")
                
        # Poll every 15 seconds to respect free tier boundaries
        await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Broadcaster stopped by user.")
