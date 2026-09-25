import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.research import Dataset as RegimeState
from tasks.regime_tasks import _refresh_regimes_async


async def run_regimes():
    print("Starting regime computation...")
    await _refresh_regimes_async()
    print("Regime computation complete.")

    async with async_session_factory() as session:
        stmt = select(RegimeState, Instrument.symbol).outerjoin(Instrument).limit(10)
        result = await session.execute(stmt)
        rows = result.all()

        print("\n--- SAMPLE REGIMES ---")
        for regime, symbol in rows:
            sym_str = symbol if symbol else "MARKET-WIDE"
            print(f"[{sym_str}] Time: {regime.time} | State: {regime.viterbi_state} | Vol: {regime.conditional_vol:.4f}")

if __name__ == "__main__":
    asyncio.run(run_regimes())
