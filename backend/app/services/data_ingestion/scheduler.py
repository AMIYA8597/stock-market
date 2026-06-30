# backend/app/services/data_ingestion/scheduler.py
"""APScheduler-based background job service for market data ingestion.

Runs during NSE market hours: 9:15 AM - 3:30 PM IST (GMT+5:30), Mon-Fri.
Skips weekends and NSE holidays.
Triggers historical backfill on startup if no data is found.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
import logging
import pytz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import get_settings
from app.database.connection import async_session_factory
from app.services.data_ingestion.orchestrator import DataIngestionOrchestrator, IngestionTask
from app.services.data_ingestion.base import Interval
from app.services.market_data_service import MarketDataService

logger = logging.getLogger("NSEMarketScheduler")
settings = get_settings()

IST = pytz.timezone("Asia/Kolkata")

# NSE Holidays for 2026 (Format: YYYY-MM-DD)
NSE_HOLIDAYS_2026 = {
    "2026-01-26",  # Republic Day
    "2026-03-06",  # Holi
    "2026-03-14",  # Good Friday
    "2026-04-02",  # Mahavir Jayanti
    "2026-04-10",  # Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-08-15",  # Independence Day
    "2026-10-02",  # Gandhi Jayanti
    "2026-12-25",  # Christmas
}

# Universe: NIFTY50 + BANKNIFTY constituents (~56 unique symbols)
UNIVERSE_SYMBOLS = list(set(MarketDataService.NSE_NIFTY50 + [
    "FEDERALBNK.NS", "IDFCFIRSTB.NS", "AUBANK.NS", "BANDHANBNK.NS", "PNB.NS", "BANKBARODA.NS"
]))


def is_market_hours() -> bool:
    """Check if current time is within Indian Stock Market hours (9:15am-3:30pm IST, Mon-Fri)."""
    now_ist = datetime.now(IST)
    
    # Check if weekend
    if now_ist.weekday() >= 5:
        return False
        
    # Check if holiday
    date_str = now_ist.strftime("%Y-%m-%d")
    if date_str in NSE_HOLIDAYS_2026:
        return False
        
    # Check market time boundaries: 9:15 AM to 3:30 PM
    market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_start <= now_ist <= market_end


class NSEMarketScheduler:
    """Orchestrates the background market data collection and backfill scheduler."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = DataIngestionOrchestrator(max_concurrency=4)
        self._backfill_running = False
        
    async def poll_market_data(self):
        """Job function running every minute to poll recent bars for all symbols in the universe."""
        if not is_market_hours():
            logger.debug("Skipping market polling: Outside market hours.")
            return

        logger.info("Starting scheduled market data poll...")
        now = datetime.now(pytz.UTC)
        start_time = now - timedelta(minutes=15)  # Fetch recent 15 minutes to capture last closing candles
        
        tasks = []
        for symbol in UNIVERSE_SYMBOLS:
            # Poll both 1m and 5m intervals during market hours
            for interval in ["1m", "5m"]:
                tasks.append(
                    IngestionTask(
                        symbol=symbol,
                        interval=interval,
                        start=start_time,
                        end=now,
                        asset_type="EQUITY"
                    )
                )

        try:
            results = await self.orchestrator.fetch_many(tasks)
            
            async with async_session_factory() as session:
                # Resolve symbol ticker to ID mapping
                stmt = text("SELECT id, ticker FROM symbols WHERE is_active = true")
                db_res = await session.execute(stmt)
                symbol_mapping = {row[1].upper(): row[0] for row in db_res.all()}
                
                success_count = 0
                for task in tasks:
                    symbol_id = symbol_mapping.get(task.symbol.upper())
                    if not symbol_id:
                        continue
                        
                    task_res = results.get(task.symbol)
                    if task_res and task_res["ok"]:
                        bars = task_res["bars"]
                        # Filter bars within requested query interval
                        filtered_bars = [b for b in bars if b.interval == task.interval]
                        if filtered_bars:
                            await self.orchestrator.persist_ohlcv(session, symbol_id, filtered_bars)
                            success_count += len(filtered_bars)
                
                await session.commit()
                logger.info(f"Market data poll completed: persisted {success_count} bars.")
        except Exception as e:
            logger.error(f"Error occurred during market data polling job: {e}", exc_info=True)

    async def perform_backfill(self):
        """Historical backfill script to download past daily and intraday bars if DB is empty."""
        if self._backfill_running:
            return
        
        self._backfill_running = True
        logger.info("Initializing historical backfill check...")
        
        try:
            async with async_session_factory() as session:
                # 1. Ensure symbols exist in the DB first
                for sym in UNIVERSE_SYMBOLS:
                    name = sym.split(".")[0]
                    exchange = "NSE"
                    asset_type = "EQUITY"
                    
                    stmt = text(
                        """
                        INSERT INTO symbols (ticker, name, exchange, asset_type, currency, is_active)
                        VALUES (:ticker, :name, :exchange, :asset_type, 'INR', true)
                        ON CONFLICT (ticker) DO NOTHING
                        """
                    )
                    await session.execute(stmt, {"ticker": sym, "name": name, "exchange": exchange, "asset_type": asset_type})
                await session.commit()
                
                # Check if we have OHLCV records
                res = await session.execute(text("SELECT COUNT(*) FROM ohlcv"))
                row_count = res.scalar() or 0
                
                if row_count > 0:
                    logger.info(f"Database contains {row_count} bars. Skipping initial backfill.")
                    self._backfill_running = False
                    return
                
                logger.info("Database is empty. Initiating historical backfill for the universe...")
                
                # Load symbols mapping
                stmt = text("SELECT id, ticker FROM symbols")
                db_res = await session.execute(stmt)
                symbol_mapping = {row[1].upper(): row[0] for row in db_res.all()}
                
            # Perform backfill in batches to avoid rate limit
            now = datetime.now(pytz.UTC)
            
            # Historical horizons:
            # 1d -> last 1 year
            # 1h -> last 60 days
            # 15m -> last 30 days
            # 5m -> last 10 days
            # 1m -> last 3 days
            backfill_configs: list[tuple[Interval, datetime]] = [
                ("1d", now - timedelta(days=365)),
                ("1h", now - timedelta(days=60)),
                ("15m", now - timedelta(days=30)),
                ("5m", now - timedelta(days=10)),
                ("1m", now - timedelta(days=3)),
            ]
            
            for interval, start_date in backfill_configs:
                logger.info(f"Backfilling interval={interval} from {start_date.date()}...")
                
                # Stagger requests by symbol to prevent rate-limiting
                for symbol in UNIVERSE_SYMBOLS:
                    symbol_id = symbol_mapping.get(symbol.upper())
                    if not symbol_id:
                        continue
                        
                    task = IngestionTask(
                        symbol=symbol,
                        interval=interval,
                        start=start_date,
                        end=now,
                        asset_type="EQUITY"
                    )
                    
                    try:
                        source_name, bars = await self.orchestrator.fetch_task(task)
                        if bars:
                            async with async_session_factory() as session:
                                count = await self.orchestrator.persist_ohlcv(session, symbol_id, bars)
                                await session.commit()
                                logger.debug(f"Persisted {count} bars for {symbol} ({interval}) via {source_name}")
                        await asyncio.sleep(0.5)  # 500ms safety throttle
                    except Exception as sym_err:
                        logger.warning(f"Failed to backfill {symbol} ({interval}): {sym_err}")
                        
            logger.info("Historical universe backfill completed successfully.")
        except Exception as e:
            logger.error(f"Error during historical backfill execution: {e}", exc_info=True)
        finally:
            self._backfill_running = False

    def start(self):
        """Start the background scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started successfully.")
            
            # Schedule polling job: runs every 1 minute during market hours
            self.scheduler.add_job(
                self.poll_market_data,
                "interval",
                minutes=1,
                id="market_data_polling_job",
                replace_existing=True
            )
            logger.info("Market polling job (1m interval) added to scheduler.")
            
            # Trigger backfill check asynchronously
            asyncio.create_task(self.perform_backfill())

    def shutdown(self):
        """Stop the background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler shut down successfully.")


# Singleton scheduler instance
market_scheduler = NSEMarketScheduler()
