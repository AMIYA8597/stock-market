"""Celery tasks for monitoring model drift and triggering retraining."""

import logging

import numpy as np
import pandas as pd
from celery import shared_task

from research.feature_engineering.pipeline import FeaturePipeline
from tasks.training_tasks import run_training_pipeline_task

logger = logging.getLogger(__name__)

def compute_psi(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    """Calculate the Population Stability Index (PSI) between two distributions."""
    def calculate_distribution(series: pd.Series, bins: np.ndarray) -> np.ndarray:
        counts, _ = np.histogram(series.dropna(), bins=bins)
        return counts / (sum(counts) + 1e-10)

    # Use expected series to define bins
    # Ensure min/max cover both series to prevent out of bounds
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())
    bins = np.linspace(min_val, max_val, buckets + 1)

    expected_dist = calculate_distribution(expected, bins)
    actual_dist = calculate_distribution(actual, bins)

    # Avoid zero division
    expected_dist = np.where(expected_dist == 0, 0.0001, expected_dist)
    actual_dist = np.where(actual_dist == 0, 0.0001, actual_dist)

    psi = np.sum((actual_dist - expected_dist) * np.log(actual_dist / expected_dist))
    return float(psi)


@shared_task
def check_drift_and_retrain(symbol: str) -> dict:
    """Check for feature drift and trigger retraining if PSI > 0.2"""
    logger.info(f"Checking drift for {symbol}")

    # Normally we'd compare the feature distribution stored at training time
    # versus the recent data (e.g. last 30 days). For this implementation,
    # we'll fetch all features and compare the oldest half to the newest half
    # to simulate training vs live distribution if we don't have stored training distributions.

    # In a full production system, ModelArtifact would store the training feature means/stds/distributions.

    # Since we need to run asyncio inside Celery, we use a wrapper
    import asyncio

    async def _async_check():
        pipeline = FeaturePipeline(symbol)
        df = await pipeline.build_features(save_to_db=False)

        if len(df) < 100:
            return {"status": "insufficient_data"}

        features = [c for c in df.columns if c not in ["time", "symbol", "close", "target_return", "target_direction"]]
        if not features:
            return {"status": "no_features"}

        # Split into "expected" (old) and "actual" (new - last 30 days)
        split_idx = len(df) - 30
        df_expected = df.iloc[:split_idx]
        df_actual = df.iloc[split_idx:]

        max_psi = 0.0
        drifted_features = []

        for feat in features:
            try:
                psi = compute_psi(df_expected[feat], df_actual[feat])
                if psi > 0.2:
                    drifted_features.append(feat)
                if psi > max_psi:
                    max_psi = psi
            except Exception as e:
                logger.warning(f"Failed to compute PSI for {feat}: {e}")

        needs_retrain = max_psi > 0.2
        logger.info(f"Max PSI for {symbol}: {max_psi:.4f}. Needs retrain: {needs_retrain}")

        if needs_retrain:
            logger.info(f"Triggering retraining for {symbol} due to drift (PSI: {max_psi:.4f})")
            # Dispatch Celery task
            run_training_pipeline_task.delay(symbol)

        return {
            "max_psi": max_psi,
            "drifted_features_count": len(drifted_features),
            "retrain_triggered": needs_retrain
        }

    return asyncio.run(_async_check())
