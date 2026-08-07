import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sqlalchemy.future import select

from app.database.connection import async_session_factory
from app.models.feature_vectors import FeatureVector
from app.models.instrument import Instrument
from app.services.ml_engine.training_pipeline import TrainingPipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

def calculate_psi(expected, actual, buckets=10):
    """Calculate the Population Stability Index (PSI) between two arrays."""
    # Ensure no NaN
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Define decile boundaries based on expected distribution
    percentiles = np.linspace(0, 100, buckets + 1)
    breakpoints = np.percentile(expected, percentiles)
    # Ensure breakpoints are strictly monotonic for digitize
    breakpoints = np.unique(breakpoints)
    if len(breakpoints) < 2:
        return 0.0

    # Digitize
    expected_counts = np.histogram(expected, bins=breakpoints)[0]
    actual_counts = np.histogram(actual, bins=breakpoints)[0]

    # Avoid div by 0
    expected_fractions = np.maximum(expected_counts / len(expected), 0.0001)
    actual_fractions = np.maximum(actual_counts / len(actual), 0.0001)

    psi_values = (expected_fractions - actual_fractions) * np.log(expected_fractions / actual_fractions)
    return np.sum(psi_values)

async def check_drift_and_retrain(symbol: str):
    logger.info(f"Checking drift for {symbol}...")
    async with async_session_factory() as session:
        res = await session.execute(select(Instrument).where(Instrument.symbol == symbol))
        instrument = res.scalars().first()
        if not instrument:
            logger.error("Instrument not found.")
            return

        # For demo/mock purposes, since DB might have static data, we just get all data and slice by index
        # (Assuming the DB has some data from phase A0)
        stmt = select(FeatureVector).where(FeatureVector.symbol_id == instrument.id).order_by(FeatureVector.time)
        result = await session.execute(stmt)
        vectors = result.scalars().all()

    if not vectors:
        logger.warning("No feature vectors found to compute drift.")
        return

    # Convert to dataframe
    df = pd.DataFrame([v.features for v in vectors])

    if len(df) < 50:
        logger.warning("Not enough data to compute drift.")
        return

    # Split into ref (first 80%) and current (last 20%) to simulate time-based drift
    split_idx = int(len(df) * 0.8)
    ref_df = df.iloc[:split_idx]
    curr_df = df.iloc[split_idx:]

    # Focus on top 5 important features (example features we expect to exist)
    target_features = ["RSI_14", "MACD_12_26_9", "ATRr_14", "ret_1d", "ret_5d"]
    features_to_check = [f for f in target_features if f in df.columns]

    if not features_to_check:
        # Fallback to some numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        features_to_check = list(numeric_cols)[:5]

    drift_detected = False
    psis = []
    ks_pvals = []

    for f in features_to_check:
        ref_val = ref_df[f].values
        curr_val = curr_df[f].values

        psi = calculate_psi(ref_val, curr_val)
        psis.append(psi)

        # KS test
        ref_val_clean = ref_val[~np.isnan(ref_val)]
        curr_val_clean = curr_val[~np.isnan(curr_val)]
        if len(ref_val_clean) > 0 and len(curr_val_clean) > 0:
            ks_stat, p_value = ks_2samp(ref_val_clean, curr_val_clean)
            ks_pvals.append(p_value)
        else:
            ks_pvals.append(1.0)

        logger.info(f"Feature '{f}': PSI = {psi:.4f}, KS p-value = {ks_pvals[-1]:.4f}")

        if psi > 0.2:
            logger.warning(f"  -> High PSI drift detected for {f}!")
            drift_detected = True
        if ks_pvals[-1] < 0.05:
            logger.warning(f"  -> Significant KS distribution shift detected for {f}!")
            drift_detected = True

    avg_psi = np.mean(psis) if psis else 0.0
    logger.info(f"Average PSI across top features: {avg_psi:.4f}")

    if drift_detected or avg_psi > 0.1:
        logger.info("Drift threshold crossed! Triggering retraining pipeline...")
        pipeline = TrainingPipeline(symbol)
        await pipeline.run()
        logger.info("Retraining complete. New artifact created.")
    else:
        logger.info("No significant drift detected. Retraining skipped.")


if __name__ == "__main__":
    asyncio.run(check_drift_and_retrain("A"))
