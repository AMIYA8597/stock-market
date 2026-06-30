# backend/scripts/seed_universe.py
"""Manual seeding script for QuantEdge stock database.

Initializes database tables, inserts the NIFTY50 and BANKNIFTY universe,
and backfills historical price data (1d, 1h, 15m, 5m, 1m timeframes).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")


async def main():
    from app.database.connection import init_db
    from app.services.data_ingestion.scheduler import market_scheduler
    
    print("Step 1: Initializing database tables...")
    await init_db()
    print("Database tables initialized successfully.")
    
    print("Step 2: Triggering historical backfill for the universe...")
    # Temporarily set backfill_running to False in case of unclean state
    market_scheduler._backfill_running = False
    
    await market_scheduler.perform_backfill()
    print("Historical backfill completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
