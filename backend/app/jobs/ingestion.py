import logging
import asyncio
from datetime import datetime, UTC, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.database.connection import async_session_factory
from app.models.market import Instrument, QuoteSnapshot, OHLCV
from app.services.ingestion.provider_manager import provider_manager

logger = logging.getLogger(__name__)

class IngestionPipeline:
    async def run_full_ingestion(self):
        """Fetches latest data for all active instruments and saves to DB."""
        logger.info("Starting full market data ingestion pipeline.")
        async with async_session_factory() as session:
            result = await session.execute(select(Instrument).where(Instrument.is_active == True))
            instruments = result.scalars().all()
            
            for inst in instruments:
                sym = inst.yfinance_ticker or inst.canonical_symbol
                try:
                    # 1. Fetch Quote
                    quote = await provider_manager.get_quote(sym)
                    if quote:
                        qs = QuoteSnapshot(
                            instrument_id=inst.id,
                            observed_at=datetime.now(UTC),
                            price=quote.price,
                            change=quote.change,
                            change_pct=quote.change_pct,
                            volume=quote.volume,
                            provider="provider_manager",
                            freshness_status="live"
                        )
                        session.add(qs)
                    
                    # 2. Fetch OHLCV
                    end = datetime.now(UTC)
                    start = end - timedelta(days=7)
                    bars = await provider_manager.get_ohlcv(sym, "1d", start, end)
                    
                    if bars:
                        for b in bars:
                            time_val = b.time
                            if time_val.tzinfo is None:
                                time_val = time_val.replace(tzinfo=UTC)

                            stmt = insert(OHLCV).values(
                                instrument_id=inst.id,
                                timestamp=time_val,
                                interval="1d",
                                open=b.open,
                                high=b.high,
                                low=b.low,
                                close=b.close,
                                volume=b.volume,
                                provider="provider_manager",
                                quality_status="valid"
                            )
                            stmt = stmt.on_conflict_do_update(
                                index_elements=['instrument_id', 'timestamp', 'interval'],
                                set_={
                                    'open': stmt.excluded.open,
                                    'high': stmt.excluded.high,
                                    'low': stmt.excluded.low,
                                    'close': stmt.excluded.close,
                                    'volume': stmt.excluded.volume,
                                }
                            )
                            await session.execute(stmt)

                except Exception as e:
                    logger.warning(f"Failed ingestion for {sym}: {e}")
            
            try:
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to commit ingestion: {e}")
                await session.rollback()
        
        logger.info("Ingestion pipeline completed.")

def setup_scheduler(app):
    # APScheduler loop removed as per architecture requirements.
    # Ingestion should be triggered by external schedulers (e.g. GitHub Actions, Celery).
    pass
