"""
Data pipeline orchestration script.

Fetches historical and real-time data from all configured sources,
normalizes it, and stores it in TimescaleDB.

Usage:
    python scripts/data_pipeline.py --symbols RELIANCE.NS,TCS.NS --period 5y
    python scripts/data_pipeline.py --universe nifty50

Fully implemented in Phase 2.
"""

from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="QuantEdge Data Pipeline")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    parser.add_argument("--universe", type=str, help="Predefined universe: nifty50, sp500, crypto50")
    parser.add_argument("--period", type=str, default="2y", help="Data period")
    args = parser.parse_args()

    print("⚠️  Data pipeline not yet implemented — coming in Phase 2")
    print(f"   Args: symbols={args.symbols}, universe={args.universe}, period={args.period}")
    sys.exit(0)


if __name__ == "__main__":
    main()
