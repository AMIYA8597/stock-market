"""Background Market Scanner for AI Alerts."""
import asyncio
import json
import logging
from datetime import UTC, datetime

from app.database.redis_client import get_redis_client
from app.services.market_data_service import MarketDataService
from app.services.prediction_engine import get_full_prediction

logger = logging.getLogger(__name__)

async def run_market_scanner():
    """Scans top symbols periodically for high conviction AI setups and publishes alerts."""
    logger.info("Starting Market Scanner background process...")

    while True:
        try:
            # Only scan top Nifty50 for global alerts to save resources
            symbols = MarketDataService.NSE_NIFTY50

            logger.info(f"Market Scanner: Scanning {len(symbols)} symbols for high conviction setups...")
            redis = await get_redis_client()

            for sym in symbols:
                try:
                    # 1. Fetch live prediction
                    pred = await get_full_prediction(sym)
                    if not pred or not pred.get("is_computed"):
                        continue

                    ens = pred.get("ensemble", {})
                    confidence = float(ens.get("confidence", 0.0))
                    direction = ens.get("direction", "NEUTRAL")

                    # 2. Only alert if confidence is high (>70%)
                    if confidence > 0.70 and direction != "NEUTRAL":
                        alert_payload = {
                            "type": "ai_alert",
                            "symbol": sym,
                            "direction": direction,
                            "confidence": confidence,
                            "rationale": f"AI Engine detected a {direction} setup with {confidence*100:.1f}% conviction.",
                            "ts": datetime.now(UTC).isoformat()
                        }

                        # Publish to alerts channel for websocket distribution
                        await redis.publish("signals:alerts", json.dumps(alert_payload))
                        logger.info(f"Published AI Alert for {sym}: {direction} @ {confidence*100:.1f}%")

                except Exception as sym_err:
                    logger.debug(f"Scanner error for {sym}: {sym_err}")

                # Rate limit the scanner
                await asyncio.sleep(2.0)

        except Exception as e:
            logger.error(f"Market Scanner failed: {e}")

        # Run scan every 1 hour
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_market_scanner())
