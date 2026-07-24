"""Backfills historical ML signals for all symbols in the database."""

import argparse
import asyncio
import logging
import os
import sys
from datetime import UTC
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")

from app.models.asset import Symbol

from app.database.connection import async_session_factory
from app.models.ohlcv import OHLCV
from app.models.signal import EnsembleSignal
from app.services.prediction_engine import build_ensemble_signal, standardize_df_columns
from research.feature_engineering.price_factors import PriceFactorsBuilder
from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_signals")


async def generate_features_for_df(df: pd.DataFrame) -> pd.DataFrame:
    """Run all feature builders needed by prediction_engine."""
    df = PriceFactorsBuilder().transform(df)
    df = VolatilityFactorsBuilder().transform(df)

    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.ema(length=9, append=True)
    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.vwap(append=True)
    df.ta.adx(length=14, append=True)
    df.ta.stoch(k=14, d=3, append=True)
    df.ta.obv(append=True)
    df.ta.supertrend(length=10, multiplier=3.0, append=True)
    df.ta.cdl_pattern(name="all", append=True)

    df = df.loc[:, ~df.columns.duplicated()]
    cols_to_drop = [c for c in df.columns if "SUPERTl" in c or "SUPERTs" in c]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    expected_features = [
        "ret_1d",
        "ret_5d",
        "ret_21d",
        "momentum_63d",
        "RSI_14",
        "MACDh_12_26_9",
        "BBP_20_2.0",
        "ATRr_14",
        "ADX_14",
        "realized_vol_21d",
        "yang_zhang_vol_21d",
        "dist_52w_high",
        "dist_52w_low",
        "drawdown",
        "range_pct",
        "close_to_open",
    ]
    df = standardize_df_columns(df, expected_features)
    return df


async def backfill_symbol(session: AsyncSession, symbol_id: str, ticker: str) -> None:
    """Fetch OHLCV, compute features, generate signals, and persist."""
    logger.info(f"Starting backfill for {ticker}...")

    # Fetch all OHLCV for the symbol
    stmt = (
        select(OHLCV)
        .where(OHLCV.symbol_id == symbol_id, OHLCV.interval == "1d")
        .order_by(OHLCV.time.asc())
    )
    res = await session.execute(stmt)
    records = res.scalars().all()

    if len(records) < 200:
        logger.warning(f"Not enough OHLCV records for {ticker} ({len(records)} found). Skipping.")
        return

    # Build DataFrame
    data = []
    for r in records:
        data.append(
            {
                "time": r.time,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
            }
        )

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df = df.set_index("time").sort_index()

    # Generate features
    df = await generate_features_for_df(df)

    # Forward-fill to eliminate nans if possible
    df = df.replace([np.inf, -np.inf], np.nan).ffill().dropna()
    if df.empty:
        logger.warning(f"DataFrame became empty after dropping NaNs for {ticker}. Skipping.")
        return

    # We will generate signals for the last N days
    # (Or all available days starting from min history)
    start_idx = 200  # Give models some warmup
    if len(df) <= start_idx:
        logger.warning(
            f"Not enough valid data points for {ticker} after feature generation. Skipping."
        )
        return

    logger.info(f"Generating signals for {len(df) - start_idx} days for {ticker}...")

    new_signals = []
    for idx in range(start_idx, len(df)):
        df_slice = df.iloc[:idx]
        current_date = df.index[idx - 1]

        # Build ensemble signal
        try:
            ens = await build_ensemble_signal(ticker, df_slice)
        except Exception as e:
            logger.error(f"Failed to generate signal for {ticker} on {current_date}: {e}")
            continue

        raw_ensemble = ens.get("raw_ensemble", 0.0)
        kelly = ens.get("kelly", 0.05)

        sig_dt = current_date
        if not sig_dt.tzinfo:
            sig_dt = sig_dt.replace(tzinfo=UTC)

        new_signals.append(
            EnsembleSignal(
                symbol_id=symbol_id,
                time=sig_dt,
                signal=raw_ensemble,
                kelly_fraction=kelly,
                metadata_json=ens.get("model_signals", {}),
            )
        )

    if not new_signals:
        return

    # Clear old signals and insert new ones
    logger.info(f"Saving {len(new_signals)} signals to database for {ticker}...")

    # We can delete existing signals for this symbol
    from sqlalchemy import delete

    del_stmt = delete(EnsembleSignal).where(EnsembleSignal.symbol_id == symbol_id)
    await session.execute(del_stmt)

    # Bulk insert
    session.add_all(new_signals)
    await session.commit()
    logger.info(f"Backfill complete for {ticker}")


async def main():
    parser = argparse.ArgumentParser(description="Backfill historical signals")
    parser.add_argument(
        "--symbols", nargs="+", help="Specific symbols to backfill (e.g. AAPL MSFT)"
    )
    args = parser.parse_args()

    async with async_session_factory() as session:
        stmt = select(Symbol)
        if args.symbols:
            stmt = stmt.where(Symbol.ticker.in_(args.symbols))

        res = await session.execute(stmt)
        symbols = res.scalars().all()

        if not symbols:
            logger.error("No symbols found in the database.")
            return

        logger.info(f"Found {len(symbols)} symbols to backfill.")

        for sym in symbols:
            await backfill_symbol(session, sym.id, sym.ticker)

    logger.info("Signal backfill complete.")


if __name__ == "__main__":
    asyncio.run(main())
