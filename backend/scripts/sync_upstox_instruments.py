"""Run the Upstox instrument-master sync directly (no Celery worker needed).

Cloud Run only runs the web process - there's no separate Celery worker
consuming tasks from Redis, so app.tasks.upstox_instrument_tasks.sync_upstox_instruments
can't be dispatched with .delay(). This calls the same underlying async
function directly, meant to run as a one-off Cloud Run Job (the same
approach used for `alembic upgrade head` earlier), e.g.:

    gcloud run jobs create sync-upstox-instruments \\
        --image <the same image already deployed> \\
        --region asia-south1 \\
        --command python --args scripts/sync_upstox_instruments.py
    gcloud run jobs execute sync-upstox-instruments --region asia-south1 --wait
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.tasks.upstox_instrument_tasks import _sync_upstox_instruments_async  # noqa: E402


async def main() -> None:
    result = await _sync_upstox_instruments_async(create_missing=True)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
