import asyncio
import logging
from decimal import Decimal

import pandas as pd
from sqlalchemy import select

from app.core.config import get_settings
from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV
from app.models.regime_states import RegimeState
from app.services.regime_analyzer import GARCHVolatilityModel, HMMRegimeModel
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

async def _process_symbol_regime(symbol_id: int | None, df: pd.DataFrame):
    """Process a single symbol or market-wide (if symbol_id is None) to generate RegimeState."""
    if df.empty or len(df) < 100:
        logger.warning(f"Not enough data for regime detection (symbol_id={symbol_id}).")
        return

    # Calculate daily log returns
    import numpy as np
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))

    # Needs a minimum number of valid returns
    if df['log_return'].dropna().shape[0] < 100:
         return

    # 1. Fit GARCH
    garch_model = GARCHVolatilityModel()
    garch_model.fit(df['log_return'])

    if garch_model.result is None:
         return

    forecasts = garch_model.forecast(horizon=21)
    cond_vol = Decimal(str(round(forecasts[0], 6)))
    vol_5d = Decimal(str(round(forecasts[4], 6))) if len(forecasts) >= 5 else cond_vol
    vol_21d = Decimal(str(round(forecasts[20], 6))) if len(forecasts) >= 21 else cond_vol

    # Add volatility as feature for HMM
    # In-sample conditional volatility from GARCH is stored in conditional_volatility
    var = garch_model.result.conditional_volatility
    # var is conditional volatility of the scaled returns (in percent). So divide by 100 to get decimal.
    df['cond_vol'] = var / 100.0

    features_df = df[['log_return', 'cond_vol']].dropna()

    # 2. Fit HMM
    hmm_model = HMMRegimeModel(n_states=3)
    hmm_model.fit(features_df)

    if hmm_model.model is None:
         return

    viterbi_state, probs = hmm_model.predict(features_df)

    # Align to the semantic labels, though we just store the viterbi state based on raw output
    # But wait, the schema expects viterbi_state (0=bull, 1=bear, 2=sideways, 3=crisis).
    # The HMM maps states arbitrarily, we must map them semantically.
    mapping = hmm_model.map_states_to_labels(features_df)

    # Inverse map semantic label to integer standard
    semantic_to_int = {"bull": 0, "bear": 1, "sideways": 2, "crisis": 3}
    semantic_label = mapping.get(viterbi_state, "sideways")
    standard_state = semantic_to_int[semantic_label]

    # Re-order probs to match standard state order: [bull, bear, sideways, crisis]
    # Default everything to 0
    standard_probs = [0.0] * 4
    for hmm_state_idx, prob in enumerate(probs):
         sem_label = mapping.get(hmm_state_idx, "sideways")
         std_idx = semantic_to_int[sem_label]
         standard_probs[std_idx] += float(round(prob, 6))

    # Save models
    settings = get_settings()
    sym_str = f"symbol_{symbol_id}" if symbol_id is not None else "market"
    garch_model.save_model(settings.model_checkpoint_path / f"garch_{sym_str}.pkl")
    hmm_model.save_model(settings.model_checkpoint_path / f"hmm_{sym_str}.pkl")

    # Upsert to DB
    last_time = df['time'].iloc[-1]

    async with async_session_factory() as session:
        # Check if exists
        stmt = select(RegimeState).where(
            RegimeState.time == last_time,
            RegimeState.symbol_id == symbol_id
        )
        res = await session.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.viterbi_state = standard_state
            existing.state_probs = standard_probs
            existing.conditional_vol = cond_vol
            existing.vol_forecast_5d = vol_5d
            existing.vol_forecast_21d = vol_21d
        else:
            new_state = RegimeState(
                time=last_time,
                symbol_id=symbol_id,
                viterbi_state=standard_state,
                state_probs=standard_probs,
                conditional_vol=cond_vol,
                vol_forecast_5d=vol_5d,
                vol_forecast_21d=vol_21d
            )
            session.add(new_state)

        await session.commit()
        logger.info(f"Regime computed for {sym_str} at {last_time}: {semantic_label} (Vol: {cond_vol})")


async def _refresh_regimes_async():
    async with async_session_factory() as session:
        inst_res = await session.execute(select(Instrument).where(Instrument.is_active))
        instruments = inst_res.scalars().all()

    market_dfs = []

    for inst in instruments:
        async with async_session_factory() as session:
            stmt = select(OHLCV).where(OHLCV.symbol_id == inst.id).order_by(OHLCV.time.asc()).limit(500) # last 500 days
            res = await session.execute(stmt)
            bars = res.scalars().all()

        if not bars:
            continue

        df = pd.DataFrame([{
            'time': b.time,
            'close': float(b.close)
        } for b in bars])

        await _process_symbol_regime(inst.id, df.copy())

        df.set_index('time', inplace=True)
        market_dfs.append(df[['close']])

    # Market-wide regime
    if market_dfs:
        # Concatenate and compute average return per day
        all_close = pd.concat(market_dfs, axis=1)
        # Calculate daily returns for each asset
        import numpy as np
        all_returns = np.log(all_close / all_close.shift(1))
        # Average return across all active assets
        market_returns = all_returns.mean(axis=1).dropna()

        if len(market_returns) > 100:
            market_df = pd.DataFrame({
                'time': market_returns.index,
                # Construct an artificial "price" series so that log_return calculation matches
                'close': np.exp(market_returns).cumprod()
            })
            await _process_symbol_regime(None, market_df)

@celery_app.task(name="tasks.regime_tasks.refresh_regime_states")
def refresh_regime_states():
    """Celery task to compute GARCH/HMM regime states for all active symbols + market proxy."""
    asyncio.run(_refresh_regimes_async())
