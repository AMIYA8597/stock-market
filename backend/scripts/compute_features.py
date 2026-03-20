"""Compute and persist feature vectors from OHLCV history."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.core.database import async_session_factory
from research.feature_engineering.pipeline import FeaturePipeline


def _sanitize_features(row: pd.Series) -> dict[str, float]:
    excluded = {
        "time",
        "symbol",
        "symbol_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "interval",
        "exchange",
        "sector",
        "industry",
        "name",
    }
    features: dict[str, float] = {}
    for key, value in row.items():
        if key in excluded:
            continue
        if isinstance(value, (int, float, np.floating, np.integer)):
            if np.isfinite(float(value)):
                features[key] = float(value)
    return features


async def _load_ohlcv(interval: str) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT o.time,
               o.symbol_id,
               s.ticker AS symbol,
               s.exchange,
               s.sector,
               s.industry,
               s.name,
               o.open,
               o.high,
               o.low,
               o.close,
               o.volume,
               o.adjusted_close,
               o.interval
        FROM ohlcv o
        JOIN symbols s ON s.id = o.symbol_id
        WHERE o.interval = :interval
        ORDER BY o.symbol_id, o.time ASC
        """
    )
    async with async_session_factory() as session:
        rows = (await session.execute(query, {"interval": interval})).mappings().all()
        return [dict(row) for row in rows]


async def compute_features(interval: str = "1d", batch_size: int = 1000) -> None:
    rows = await _load_ohlcv(interval=interval)
    if not rows:
        print(f"No OHLCV data found for interval={interval}.")
        return

    frame = pd.DataFrame(rows)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)

    pipeline = FeaturePipeline()
    insert_stmt = text(
        """
        INSERT INTO feature_vectors (time, symbol_id, features, feature_version)
        VALUES (:time, :symbol_id, CAST(:features AS jsonb), :feature_version)
        ON CONFLICT (time, symbol_id)
        DO UPDATE SET
          features = EXCLUDED.features,
          feature_version = EXCLUDED.feature_version
        """
    )

    payload: list[dict[str, Any]] = []
    for symbol_id, group in frame.groupby("symbol_id", sort=False):
        engineered = pipeline.run(group)
        for _, row in engineered.iterrows():
            features = _sanitize_features(row)
            if not features:
                continue
            payload.append(
                {
                    "time": row["time"],
                    "symbol_id": int(symbol_id),
                    "features": json.dumps(features),
                    "feature_version": "v1",
                }
            )

    if not payload:
        print("No feature rows generated.")
        return

    total = 0
    async with async_session_factory() as session:
        for i in range(0, len(payload), batch_size):
            chunk = payload[i : i + batch_size]
            await session.execute(insert_stmt, chunk)
            total += len(chunk)
        await session.commit()

    print(f"Feature computation complete. Upserted rows: {total}")


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Compute feature vectors from OHLCV")
    parser.add_argument("--interval", default="1d", help="OHLCV interval to process")
    parser.add_argument("--batch-size", type=int, default=1000, help="DB upsert batch size")
    args = parser.parse_args()

    asyncio.run(compute_features(interval=args.interval, batch_size=args.batch_size))
