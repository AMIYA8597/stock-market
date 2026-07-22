"""Celery tasks for background market data ingestion."""
import logging
from datetime import datetime
from celery import shared_task

from app.services.data_ingestion.provider_manager import provider_manager
from app.services.data_ingestion.base import IngestionTask

logger = logging.getLogger(__name__)

@shared_task(name="market_data.backfill")
def backfill_market_data(symbol: str, interval: str, start_date_str: str, end_date_str: str) -> dict:
    import asyncio
    
    start = datetime.fromisoformat(start_date_str)
    end = datetime.fromisoformat(end_date_str)
    
    task = IngestionTask(
        symbol=symbol,
        asset_type="EQUITY",
        interval=interval,
        start=start,
        end=end,
    )
    
    async def run_fetch():
        return await provider_manager.fetch(task)
        
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        bars = loop.run_until_complete(run_fetch())
        logger.info(f"Successfully backfilled {len(bars)} bars for {symbol}")
        return {"status": "success", "bars_fetched": len(bars)}
    except Exception as e:
        logger.error(f"Failed to backfill {symbol}: {e}")
        return {"status": "error", "error": str(e)}
