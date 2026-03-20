"""Verify required schema objects for new-prompt baseline."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.database import async_session_factory

REQUIRED_TABLES = {
    "users",
    "symbols",
    "ohlcv",
    "feature_vectors",
    "regime_states",
    "ml_predictions",
    "ensemble_signals",
    "portfolio_holdings",
    "transactions",
    "alerts",
    "backtest_jobs",
    "news_sentiment",
}


async def verify_schema() -> int:
    async with async_session_factory() as session:
        tables = (
            await session.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            )
        ).scalars().all()

        table_set = set(tables)
        missing = sorted(REQUIRED_TABLES - table_set)

        ext_rows = (
            await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname IN ('timescaledb', 'pgcrypto')")
            )
        ).scalars().all()
        extensions = set(ext_rows)

        cagg_exists = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pg_matviews
                    WHERE matviewname = 'ohlcv_1h'
                    """
                )
            )
        ).scalar_one()

    print("Schema Verification Report")
    print("------------------------")
    print(f"Tables found: {len(table_set)}")
    print(f"Required tables missing: {missing if missing else 'none'}")
    print(f"Extensions: {sorted(extensions)}")
    print(f"Continuous aggregate ohlcv_1h exists: {bool(cagg_exists)}")

    if missing:
        return 1
    if "timescaledb" not in extensions:
        return 1
    if not cagg_exists:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(verify_schema()))
