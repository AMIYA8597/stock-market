"""Operational data pipeline CLI for ingestion and feature generation."""

from __future__ import annotations

import argparse
import asyncio

from pipelines.data_pipeline import run_full_history
from scripts.compute_features import compute_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QuantEdge Data Pipeline")
    parser.add_argument("--full-history", action="store_true", help="Ingest default 5-year universe history")
    parser.add_argument("--features-only", action="store_true", help="Compute feature vectors from existing OHLCV")
    parser.add_argument("--years", type=int, default=5, help="History depth in years for --full-history")
    parser.add_argument("--interval", type=str, default="1d", help="Interval for feature computation")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for feature upserts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.full_history:
        asyncio.run(run_full_history(years=args.years))

    if args.features_only:
        asyncio.run(compute_features(interval=args.interval, batch_size=args.batch_size))

    if not args.full_history and not args.features_only:
        raise SystemExit("Use --full-history and/or --features-only")


if __name__ == "__main__":
    main()
