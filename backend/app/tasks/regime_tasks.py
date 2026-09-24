"""Celery tasks for Regime and Volatility calculation."""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from celery import shared_task
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV
from app.models.regime_states import RegimeState
from research.models.hmm_garch.inference import InferenceEngine

logger = logging.getLogger(__name__)


@shared_task(name="update_regime_states", bind=True, max_retries=3)
def update_regime_states(self: Any) -> dict[str, Any]:
    """Run GARCH and HMM for active symbols and save the regime state."""
    return asyncio.run(_update_regime_states_async())


async def _update_regime_states_async() -> dict[str, Any]:
    logger.info("Starting regime and volatility update...")

    records_updated = 0

    async with async_session_factory() as session:
        # Fetch active instruments
        result = await session.execute(select(Instrument).where(Instrument.is_active))
        instruments = result.scalars().all()

        for inst in instruments:
            # Fetch last 3 years of OHLCV to have enough data for HMM/GARCH
            ohlcv_res = await session.execute(
                select(OHLCV)
                .where(OHLCV.symbol_id == inst.id)
                .order_by(OHLCV.time.desc())
                .limit(750)
            )
            ohlcv_records = ohlcv_res.scalars().all()

            if len(ohlcv_records) < 100:
                logger.warning(f"Not enough data for {inst.symbol}. Need at least 100 days.")
                continue

            # Convert to DataFrame (reverse to be chronological)
            df = pd.DataFrame(
                [
                    {
                        "time": r.time,
                        "close": float(r.close),
                    }
                    for r in reversed(ohlcv_records)
                ]
            )

            df.set_index("time", inplace=True)

            # Compute daily log returns
            df["returns"] = np.log(df["close"] / df["close"].shift(1))

            # Compute a rolling volatility (used as a 2nd feature for HMM)
            df["volatility_20d"] = df["returns"].rolling(20).std() * np.sqrt(252)

            # Use the canonical InferenceEngine which wraps StudentTHMM and arch GARCH
            # We rebuild df correctly from ohlcv_records
            df_full = pd.DataFrame([
                {
                    "time": r.time,
                    "open": float(r.open) if hasattr(r, 'open') else float(r.close),
                    "high": float(r.high) if hasattr(r, 'high') else float(r.close),
                    "low": float(r.low) if hasattr(r, 'low') else float(r.close),
                    "close": float(r.close),
                    "volume": float(r.volume) if hasattr(r, 'volume') else 0.0
                }
                for r in reversed(ohlcv_records)
            ])
            df_full.set_index("time", inplace=True)
            
            ohlcv_data = df_full[["open", "high", "low", "close", "volume"]].astype(float).values
            
            engine = InferenceEngine()
            res = engine.predict(ohlcv_data, train=True)
            
            canonical_state_idx = res.current_state
            
            canonical_probs = [0.0, 0.0, 0.0, 0.0]
            for i in range(len(res.state_probs)):
                if i < 4:
                    canonical_probs[i] = float(res.state_probs[i])
                    
            cond_vol_1d = float(res.conditional_vol)
            cond_vol_5d = float(res.vol_forecast_5d)
            cond_vol_21d = float(res.vol_forecast_21d)

            # Safe boundary checks
            cond_vol_1d = max(0.001, min(2.0, cond_vol_1d))
            cond_vol_5d = max(0.001, min(2.0, cond_vol_5d))
            cond_vol_21d = max(0.001, min(2.0, cond_vol_21d))

            latest_time = df.index[-1]

            # Upsert into DB
            existing = await session.execute(
                select(RegimeState).where(
                    RegimeState.time == latest_time, RegimeState.symbol_id == inst.id
                )
            )
            regime = existing.scalars().first()

            if regime:
                regime.viterbi_state = canonical_state_idx
                regime.state_probs = [float(round(p, 4)) for p in canonical_probs]
                regime.conditional_vol = Decimal(str(round(cond_vol_1d, 6)))
                regime.vol_forecast_5d = Decimal(str(round(cond_vol_5d, 6)))
                regime.vol_forecast_21d = Decimal(str(round(cond_vol_21d, 6)))
            else:
                regime = RegimeState(
                    time=latest_time,
                    symbol_id=inst.id,
                    viterbi_state=canonical_state_idx,
                    state_probs=[float(round(p, 4)) for p in canonical_probs],
                    conditional_vol=Decimal(str(round(cond_vol_1d, 6))),
                    vol_forecast_5d=Decimal(str(round(cond_vol_5d, 6))),
                    vol_forecast_21d=Decimal(str(round(cond_vol_21d, 6))),
                )
                session.add(regime)

            records_updated += 1

        if records_updated > 0:
            await session.commit()

    logger.info(f"Regime and volatility update complete. Processed {records_updated} symbols.")
    return {"status": "success", "records_updated": records_updated}


# We need numpy
