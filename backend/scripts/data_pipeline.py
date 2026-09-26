"""Operational data pipeline CLI for ingestion and feature generation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import asyncio

from app.tasks.market_data_tasks import (
    _backfill_crypto_historical_data_async,
    _backfill_historical_data_async,
    _seed_crypto_universe_async,
    _seed_universe_async,
)
from scripts.compute_features import compute_features


async def run_full_history(years: int) -> None:
    """Seed the NSE universe (if not already seeded) then backfill OHLCV history."""
    await _seed_universe_async()
    await _backfill_historical_data_async(years=years)


async def run_crypto_history(years: int) -> None:
    """Seed active USDT-quoted Binance pairs, then backfill OHLCV history."""
    await _seed_crypto_universe_async()
    await _backfill_crypto_historical_data_async(years=years)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QuantEdge Data Pipeline")
    parser.add_argument(
        "--full-history", action="store_true", help="Ingest default 5-year NSE equity history"
    )
    parser.add_argument(
        "--crypto-history",
        action="store_true",
        help="Ingest USDT-quoted Binance pairs + their OHLCV history",
    )
    parser.add_argument(
        "--features-only", action="store_true", help="Compute feature vectors from existing OHLCV"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="History depth in years for --full-history/--crypto-history",
    )
    parser.add_argument(
        "--interval", type=str, default="1d", help="Interval for feature computation"
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for feature upserts"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.full_history:
        asyncio.run(run_full_history(years=args.years))

    if args.crypto_history:
        asyncio.run(run_crypto_history(years=args.years))

    if args.features_only:
        asyncio.run(compute_features(interval=args.interval, batch_size=args.batch_size))

    if not args.full_history and not args.crypto_history and not args.features_only:
        raise SystemExit("Use --full-history, --crypto-history, and/or --features-only")


if __name__ == "__main__":
    main()
