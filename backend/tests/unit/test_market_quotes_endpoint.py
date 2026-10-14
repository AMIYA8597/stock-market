from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.market import get_quotes_batch


@pytest.mark.asyncio
async def test_batch_quotes_preserve_provider_timestamp_and_freshness() -> None:
    observed_at = datetime.now(UTC) - timedelta(seconds=7)
    payload = {
        "RELIANCE": {
            "price": 2500,
            "change": 10,
            "change_pct": 0.4,
            "volume": 100,
            "timestamp": observed_at.isoformat(),
            "source": "upstox",
        }
    }

    with patch(
        "app.api.v1.market.MarketDataService.get_batch_quotes",
        new=AsyncMock(return_value=payload),
    ):
        result = await get_quotes_batch("RELIANCE", None)

    quote = result["RELIANCE"]
    assert quote.timestamp == observed_at
    assert quote.data_freshness_seconds is not None
    assert 6 <= quote.data_freshness_seconds <= 9
    assert quote.source == "upstox"


@pytest.mark.asyncio
async def test_batch_quotes_skip_invalid_provider_timestamp() -> None:
    payload = {"RELIANCE": {"price": 2500, "timestamp": "not-a-timestamp"}}

    with patch(
        "app.api.v1.market.MarketDataService.get_batch_quotes",
        new=AsyncMock(return_value=payload),
    ):
        result = await get_quotes_batch("RELIANCE", None)

    assert result == {}
