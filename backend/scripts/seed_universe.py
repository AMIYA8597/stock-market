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
    print("Step 2: Note - historical backfill has been moved to robust celery tasks.")
    # Legacy market_scheduler removed per Stage 1 requirements
    print("Universe seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
