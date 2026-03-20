"""Run strict sequential backend build steps end-to-end.

Sequence:
1) Verify migrated schema and Timescale extensions.
2) Ingest full-history market data.
3) Compute feature vectors.
4) Train enabled models (HMM/TFT/GNN).
"""

from __future__ import annotations

import argparse
import asyncio
import json

from scripts.compute_features import compute_features
from scripts.model_trainer import run_training
from scripts.verify_schema import verify_schema
from pipelines.data_pipeline import run_full_history


async def run_all(years: int, interval: str, batch_size: int, model: str, symbol: str, universe: str, epochs: int) -> int:
    report: dict[str, object] = {"steps": []}

    schema_code = await verify_schema()
    report["steps"].append({"step": "verify_schema", "exit_code": schema_code})
    if schema_code != 0:
        print(json.dumps(report, indent=2))
        return schema_code

    await run_full_history(years=years)
    report["steps"].append({"step": "run_full_history", "status": "ok", "years": years})

    await compute_features(interval=interval, batch_size=batch_size)
    report["steps"].append(
        {"step": "compute_features", "status": "ok", "interval": interval, "batch_size": batch_size}
    )

    model_code = await run_training(
        model=model,
        symbol=symbol,
        universe=universe,
        interval=interval,
        epochs=epochs,
    )
    report["steps"].append({"step": "model_training", "exit_code": model_code, "model": model})

    print(json.dumps(report, indent=2))
    return model_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full sequential backend build")
    parser.add_argument("--years", type=int, default=5, help="History years for ingestion")
    parser.add_argument("--interval", type=str, default="1d", help="OHLCV interval")
    parser.add_argument("--batch-size", type=int, default=1000, help="Feature upsert batch size")
    parser.add_argument("--model", type=str, default="all", help="Model selection for training")
    parser.add_argument("--symbol", type=str, default="NIFTY", help="Ticker for single-symbol models")
    parser.add_argument("--universe", type=str, default="NSE", help="Universe key for cross-asset models")
    parser.add_argument("--epochs", type=int, default=20, help="Epochs for trainable deep models")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(
        run_all(
            years=args.years,
            interval=args.interval,
            batch_size=args.batch_size,
            model=args.model,
            symbol=args.symbol,
            universe=args.universe,
            epochs=args.epochs,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
