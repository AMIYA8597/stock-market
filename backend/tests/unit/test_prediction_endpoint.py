import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.predictions import get_prediction


@pytest.mark.asyncio
async def test_prediction_timeout_is_explicitly_unavailable() -> None:
    with (
        patch(
            "app.services.prediction_engine._cache_fetch",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.predictions.get_full_prediction",
            new=AsyncMock(side_effect=asyncio.TimeoutError),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_prediction("RELIANCE", AsyncMock())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error"]["code"] == "MODEL_UNAVAILABLE"
    assert exc_info.value.detail["error"]["retryable"] is True
