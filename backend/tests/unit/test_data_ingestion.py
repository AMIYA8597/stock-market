from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.data_ingestion.base import (
    DataUnavailableError,
    MarketDataProvider,
    OHLCVBar,
    Quote,
)
from app.services.data_ingestion.provider_manager import ProviderManager


class _FailingSource(MarketDataProvider):
    name = "failing"

    async def get_ohlcv(self, symbol, interval, start, end):
        raise DataUnavailableError(f"{symbol} unavailable")

    async def get_quote(self, symbol: str) -> Quote:
        raise DataUnavailableError(f"{symbol} unavailable")

    async def get_universe(self):
        return []

    async def health(self):
        return {"status": "error"}


class _SuccessSource(MarketDataProvider):
    name = "success"

    async def get_ohlcv(self, symbol, interval, start, end):
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

    async def get_quote(self, symbol: str) -> Quote:
        return Quote(symbol, 101.0, 1.0, 1.0, 1000.0, datetime.now(UTC))

    async def get_universe(self):
        return []

    async def health(self):
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_orchestrator_fallback_source_order_for_nse_symbol() -> None:
    manager = ProviderManager()
    manager.providers = [_FailingSource(), _SuccessSource()]

    bars = await manager.get_ohlcv(
        symbol="RELIANCE",
        interval="1d",
        start=datetime.now(UTC) - timedelta(days=5),
        end=datetime.now(UTC),
    )

    assert len(bars) == 1
    assert bars[0].close == 101.0


@pytest.mark.asyncio
async def test_orchestrator_returns_error_when_all_sources_fail() -> None:
    manager = ProviderManager()
    manager.providers = [_FailingSource()]

    with pytest.raises(DataUnavailableError):
        await manager.get_ohlcv(
            symbol="INVALID",
            interval="1d",
            start=datetime.now(UTC) - timedelta(days=5),
            end=datetime.now(UTC),
        )
