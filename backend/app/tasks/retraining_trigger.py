"""Celery task for monitoring feature drift and triggering retraining."""

import asyncio
import logging

import numpy as np
import pandas as pd
from celery import shared_task
from scipy.stats import ks_2samp
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.research import Dataset as FeatureVector
from app.models.research import ModelRegistry as ModelArtifact
from app.services.ml_engine.training_pipeline import TrainingPipeline

logger = logging.getLogger(__name__)


def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Calculate the Population Stability Index (PSI)."""

    def scale_range(input, min, max):
        input += -(np.min(input))
        input /= np.max(input) / (max - min)
        input += min
        return input

    breakpoints = np.arange(0, buckets + 1) / (buckets) * 100
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    breakpoints = scale_range(breakpoints, np.min(expected), np.max(expected))
    expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)

    def sub_psi(e_perc, a_perc):
        """Calculate the actual PSI value from comparing the values."""
        if a_perc == 0:
            a_perc = 0.0001
        if e_perc == 0:
            e_perc = 0.0001
        value = (e_perc - a_perc) * np.log(e_perc / a_perc)
        return value

    psi_value = np.sum(
        sub_psi(expected_percents[i], actual_percents[i]) for i in range(len(expected_percents))
    )
    return psi_value


@shared_task(name="check_model_drift_and_retrain", bind=True)
def check_model_drift_and_retrain(self, symbol: str) -> dict:
    return asyncio.run(_check_model_drift_async(symbol))


async def _check_model_drift_async(symbol: str) -> dict:
    logger.info(f"Checking model drift for {symbol}...")

    async with async_session_factory() as session:
        inst_res = await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))
        inst = inst_res.scalars().first()
        if not inst:
            logger.error(f"Instrument not found: {symbol}")
            return {"status": "error", "message": "Instrument not found"}

        # Check active model
        active_model_res = await session.execute(
            select(ModelArtifact).where(ModelArtifact.symbol_id == inst.id, ModelArtifact.is_active)
        )
        active_model = active_model_res.scalars().first()
        if not active_model:
            logger.warning("No active model found. Forcing retrain...")
            return await force_retrain(symbol)

        # Fetch features
        feat_res = await session.execute(
            select(FeatureVector)
            .where(FeatureVector.symbol_id == inst.id)
            .order_by(FeatureVector.time.asc())
        )
        vectors = feat_res.scalars().all()

    rows = [v.features for v in vectors]
    df = pd.DataFrame(rows)
    df = df.fillna(0.0)

    if len(df) < 60:
        return {"status": "skip", "message": "Not enough data to compute drift"}

    # Let's say training distribution is everything up to 30 days ago, and live is last 30 days
    train_dist = df.iloc[:-30]
    live_dist = df.iloc[-30:]

    # We will pick a few important features to monitor
    key_features = ["ret_1d", "ret_5d", "yang_zhang_vol_21d", "range_pct", "sentiment_score"]
    available_features = [f for f in key_features if f in df.columns]

    max_psi = 0.0
    drift_detected = False

    for feature in available_features:
        expected = train_dist[feature].values
        actual = live_dist[feature].values

        # KS Test
        ks_stat, p_value = ks_2samp(expected, actual)

        # PSI
        try:
            psi = calculate_psi(expected, actual)
        except Exception:
            psi = 0.0

        max_psi = max(max_psi, psi)
        logger.info(
            f"Drift metrics for {feature} -> KS: {ks_stat:.4f} (p={p_value:.4f}), PSI: {psi:.4f}"
        )

        # Threshold: if PSI > 0.2, it's significant drift. Also if KS p_value < 0.05
        if psi > 0.2 or p_value < 0.05:
            logger.warning(
                f"Significant drift detected on {feature}! PSI: {psi:.4f}, KS-p: {p_value:.4f}"
            )
            drift_detected = True

    if drift_detected:
        logger.info("Drift threshold exceeded. Triggering retrain pipeline...")
        return await force_retrain(symbol)

    return {"status": "success", "drift_detected": False, "max_psi": max_psi}


async def force_retrain(symbol: str) -> dict:
    pipeline = TrainingPipeline(symbol)
    result = await pipeline.run()
    return {"status": "retrained", "metrics": result}


@shared_task(name="check_drift_for_watchlist")
def check_drift_for_watchlist() -> dict:
    """Walk-forward drift check across the canonical watchlist.

    check_model_drift_and_retrain existed as a real, working per-symbol PSI/KS
    drift detector but was never actually scheduled anywhere — dead code that
    silently never ran. This wraps it across WATCHLIST_SYMBOLS and is the task
    that's actually registered in the Celery beat schedule.
    """
    from app.core.watchlist import WATCHLIST_SYMBOLS

    results: dict[str, str] = {}
    for symbol in WATCHLIST_SYMBOLS:
        try:
            outcome = asyncio.run(_check_model_drift_async(symbol))
            results[symbol] = outcome.get("status", "unknown")
        except Exception as e:
            logger.error(f"Drift check failed for {symbol}: {e}")
            results[symbol] = "error"
    return results


if __name__ == "__main__":
    import sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    asyncio.run(_check_model_drift_async(symbol))
