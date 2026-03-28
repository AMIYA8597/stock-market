from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.data_ingestion.base import DataSourceError, MarketDataSource, OHLCVBar
from app.services.data_ingestion.orchestrator import DataIngestionOrchestrator, IngestionTask


class _FailingSource(MarketDataSource):
    name = "failing"

    async def fetch_ohlcv(self, symbol, interval, start, end):
        raise DataSourceError(f"{symbol} unavailable")


class _SuccessSource(MarketDataSource):
    name = "success"

    async def fetch_ohlcv(self, symbol, interval, start, end):
        del symbol, interval, start
        return [
            OHLCVBar(
                time=end - timedelta(days=1),
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1000.0,
                adjusted_close=None,
                interval="1d",
            )
        ]


@pytest.mark.asyncio
async def test_orchestrator_fallback_source_order_for_nse_symbol() -> None:
    orchestrator = DataIngestionOrchestrator(max_concurrency=2)
    orchestrator._sources["nse"] = _FailingSource()  # type: ignore[attr-defined]
    orchestrator._sources["yfinance"] = _SuccessSource()  # type: ignore[attr-defined]

    task = IngestionTask(
        symbol="RELIANCE.NS",
        interval="1d",
        start=datetime.now(UTC) - timedelta(days=5),
        end=datetime.now(UTC),
        asset_type="EQUITY",
    )

    source_name, bars = await orchestrator.fetch_task(task)

    assert source_name == "success"
    assert len(bars) == 1
    assert bars[0].close == 101.0


@pytest.mark.asyncio
async def test_orchestrator_returns_error_when_all_sources_fail() -> None:
    orchestrator = DataIngestionOrchestrator(max_concurrency=2)
    failing = _FailingSource()
    orchestrator._sources["coingecko"] = failing  # type: ignore[attr-defined]
    orchestrator._sources["yfinance"] = failing  # type: ignore[attr-defined]

    task = IngestionTask(
        symbol="btc-usd",
        interval="1d",
        start=datetime.now(UTC) - timedelta(days=5),
        end=datetime.now(UTC),
        asset_type="CRYPTO",
    )

    with pytest.raises(DataSourceError):
        await orchestrator.fetch_task(task)
