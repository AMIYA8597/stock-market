"""Pipeline entrypoint for bulk market-data ingestion."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.database import async_session_factory
from app.services.data_ingestion import DataIngestionOrchestrator, IngestionTask


DEFAULT_NSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "ITC.NS",
    "BHARTIARTL.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "WIPRO.NS",
    "NESTLEIND.NS",
    "HCLTECH.NS",
    "ULTRACEMCO.NS",
    "TECHM.NS",
    "ADANIPORTS.NS",
]

DEFAULT_US = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "V", "WMT"]
DEFAULT_CRYPTO = ["btc-usd", "eth-usd", "sol-usd", "ada-usd", "bnb-usd"]


def _task_for_symbol(symbol: str, years: int) -> IngestionTask:
    end = datetime.now(tz=UTC)
    start = end - timedelta(days=365 * years)
    if symbol.endswith(".NS"):
        asset_type = "EQUITY"
    elif symbol.endswith("-usd"):
        asset_type = "CRYPTO"
    else:
        asset_type = "EQUITY"
    return IngestionTask(symbol=symbol, interval="1d", start=start, end=end, asset_type=asset_type)


async def _resolve_symbol_id(session, ticker: str) -> int:
    query = text("SELECT id FROM symbols WHERE ticker = :ticker LIMIT 1")
    result = await session.execute(query, {"ticker": ticker.upper()})
    row = result.first()
    if row:
        return int(row[0])

    insert_stmt = text(
        """
        INSERT INTO symbols (ticker, name, exchange, asset_type, currency)
        VALUES (:ticker, :name, :exchange, :asset_type, :currency)
        RETURNING id
        """
    )

    exchange = "NSE" if ticker.endswith(".NS") else "CRYPTO" if ticker.endswith("-usd") else "NYSE"
    asset_type = "CRYPTO" if ticker.endswith("-usd") else "EQUITY"
    currency = "USD"

    inserted = await session.execute(
        insert_stmt,
        {
            "ticker": ticker.upper(),
            "name": ticker.upper(),
            "exchange": exchange,
            "asset_type": asset_type,
            "currency": currency,
        },
    )
    new_id = inserted.scalar_one()
    return int(new_id)


async def run_full_history(years: int) -> None:
    orchestrator = DataIngestionOrchestrator(max_concurrency=10)
    symbols = DEFAULT_NSE + DEFAULT_US + DEFAULT_CRYPTO
    tasks = [_task_for_symbol(symbol, years=years) for symbol in symbols]
    results = await orchestrator.fetch_many(tasks)

    async with async_session_factory() as session:
        total_rows = 0
        for symbol, info in results.items():
            if not info.get("ok"):
                print(f"[ERROR] {symbol}: {info.get('error')}")
                continue
            symbol_id = await _resolve_symbol_id(session, symbol)
            inserted = await orchestrator.persist_ohlcv(session, symbol_id, info["bars"])
            total_rows += inserted
            print(f"[OK] {symbol}: {inserted} rows via {info.get('source')}")
        await session.commit()

    print(f"Ingestion completed. Total rows upserted: {total_rows}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run market data ingestion pipeline")
    parser.add_argument("--full-history", action="store_true", help="Fetch full history for default universe")
    parser.add_argument("--years", type=int, default=5, help="History depth in years")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.full_history:
        asyncio.run(run_full_history(years=args.years))
        return
    raise SystemExit("Use --full-history to run ingestion")


if __name__ == "__main__":
    main()
