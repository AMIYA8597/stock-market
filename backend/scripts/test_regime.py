import asyncio

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.research import Dataset as RegimeState
from app.tasks.regime_tasks import _update_regime_states_async


async def main():
    print("Starting regime and volatility analysis job...")
    result = await _update_regime_states_async()
    print(f"Job Result: {result}")

    # Verify DB output
    async with async_session_factory() as session:
        res = await session.execute(
            select(RegimeState).order_by(RegimeState.time.desc()).limit(1)
        )
        reg = res.scalars().first()
        if reg:
            print("\n--- Latest Regime & Volatility ---")
            print(f"Time: {reg.time}")
            print(f"Viterbi State (0=bull,1=bear,2=side): {reg.viterbi_state}")
            print(f"State Probs: {reg.state_probs}")
            print(f"Cond Vol 1d: {reg.conditional_vol}")
            print(f"Cond Vol 5d: {reg.vol_forecast_5d}")
            print(f"Cond Vol 21d: {reg.vol_forecast_21d}")

if __name__ == "__main__":
    asyncio.run(main())
