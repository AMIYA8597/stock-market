"""Run the OHLCV historical backfill directly (no Celery worker needed).

Same reasoning as scripts/sync_upstox_instruments.py - Cloud Run has no
separate Celery worker, so this calls
app.tasks.market_data_tasks._backfill_historical_data_async directly, meant
to run as a one-off Cloud Run Job:

    gcloud run jobs create backfill-historical \\
        --image <the same image already deployed> \\
        --region asia-south1 \\
        --command python --args scripts/backfill_historical.py,--years,1 \\
        --task-timeout 3600
    gcloud run jobs execute backfill-historical --region asia-south1 --wait

Defaults to 1 year rather than the task's own 5-year default: this walks
every active Instrument sequentially with a jittered delay between each to
avoid hammering the provider, so 5 years across a full NSE universe (a few
thousand instruments after the Upstox sync) would run far longer than is
practical for a first run. Pass --years to widen it once this completes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.tasks.market_data_tasks import _backfill_historical_data_async  # noqa: E402


async def main(years: int) -> None:
    await _backfill_historical_data_async(years=years)
    print(f"Backfill complete (years={years})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main(args.years))
