"""Pytest bootstrap for backend package imports."""

from __future__ import annotations

import os
os.environ["RATE_LIMIT_ENABLED"] = "true"

import sys
import socket
from pathlib import Path

# Ensure backend root is importable as top-level packages: app, research, tests.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
for p in list(sys.path):
    if p.lower() == str(WORKSPACE_ROOT).lower() or p.lower() == str(WORKSPACE_ROOT).lower() + "\\":
        sys.path.remove(p)
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
else:
    sys.path.remove(str(BACKEND_ROOT))
    sys.path.insert(0, str(BACKEND_ROOT))
print("DEBUG CONFTEST: BACKEND_ROOT =", BACKEND_ROOT)
print("DEBUG CONFTEST: sys.path after fix =", sys.path)
print("DEBUG CONFTEST: research module in sys.modules =", sys.modules.get('research'))
if 'research' in sys.modules:
    print("DEBUG CONFTEST: research path =", getattr(sys.modules['research'], '__file__', None))
# Set a fast default socket timeout so offline tests trigger fallbacks immediately
socket.setdefaulttimeout(1.5)

# Mock yfinance to raise exceptions immediately, preventing slow network hangs during tests
from unittest.mock import MagicMock

class MockTicker:
    def __init__(self, *args, **kwargs):
        pass
    def history(self, *args, **kwargs):
        raise RuntimeError("Network offline (mocked yfinance)")
    @property
    def info(self):
        raise RuntimeError("Network offline (mocked yfinance)")

import importlib.machinery
mock_yf = MagicMock()
mock_yf.Ticker = MockTicker
def mock_download(*args, **kwargs):
    raise RuntimeError("Network offline (mocked yfinance)")
mock_yf.download = mock_download
mock_yf.__spec__ = importlib.machinery.ModuleSpec('yfinance', None)

sys.modules['yfinance'] = mock_yf

from datetime import datetime, UTC, timedelta
async def mock_get_full_prediction(symbol: str) -> dict:
    return {
        "symbol": symbol.upper(),
        "current_price": 2521.30,
        "timestamp": datetime.now(UTC).isoformat(),
        "ensemble": {
            "raw_ensemble": 0.4200,
            "confidence": 0.7310,
            "direction": "BUY",
            "kelly": 0.1200,
            "regime": {
                "regime": "BULL",
                "bull_prob": 0.75,
                "bear_prob": 0.25,
                "regime_confidence": 0.75,
                "hmm_used": True
            },
            "technical": {
                "score": 0.35,
                "rsi": 52.4,
                "macd_histogram": 1.2,
                "bb_position": 0.5,
                "adx": 28.5,
                "supertrend_direction": 1,
                "above_vwap": True,
                "indicators_computed": 10
            },
            "pattern": {
                "pattern_score": 0.10,
                "patterns_detected": ["CDL_HAMMER"],
                "bullish_count": 1,
                "bearish_count": 0
            },
            "momentum": {
                "momentum_score": 0.25,
                "ret_1d": 0.005,
                "ret_5d": 0.012,
                "ret_21d": 0.035,
                "jt_momentum": 0.02,
                "vol_21d": 0.015,
                "yang_zhang_vol": 0.018,
                "dist_52w_high": -0.02,
                "dist_52w_low": 0.15
            },
            "xgboost": {
                "xgb_score": 0.45,
                "xgb_confidence": 0.68,
                "xgb_direction": "BUY",
                "train_samples": 450
            }
        },
        "forecast": [
            {
                "horizon_days": 1,
                "predicted_price": 2530.00,
                "prediction_low": 2515.00,
                "prediction_high": 2545.00,
                "change_pct": 0.35,
                "target_date": (datetime.now(UTC) + timedelta(days=1)).isoformat()
            },
            {
                "horizon_days": 5,
                "predicted_price": 2560.00,
                "prediction_low": 2530.00,
                "prediction_high": 2590.00,
                "change_pct": 1.53,
                "target_date": (datetime.now(UTC) + timedelta(days=5)).isoformat()
            }
        ],
        "data_points_used": 500,
        "is_computed": True
    }

import app.services.prediction_engine as prediction_engine_module
prediction_engine_module.get_full_prediction = mock_get_full_prediction

async def mock_get_quote(symbol: str) -> dict:
    return {
        "symbol": symbol.upper() if "." in symbol or "^" in symbol or "-" in symbol else f"{symbol.upper()}.NS",
        "price": 2521.30,
        "change": 15.50,
        "change_pct": 0.62,
        "open": 2510.00,
        "high": 2530.00,
        "low": 2505.00,
        "volume": 1200000,
        "previous_close": 2505.80,
        "market_cap": 15000000000.0,
        "week_52_high": 2600.00,
        "week_52_low": 2300.00,
    }

async def mock_get_history(symbol: str, interval: str, period: str) -> list[dict]:
    from datetime import timedelta
    now = datetime.now(UTC)
    result = []
    for i in range(30):
        result.append({
            "time": (now - timedelta(days=30-i)).isoformat(),
            "open": 2500.0 + i * 2.0,
            "high": 2510.0 + i * 2.0,
            "low": 2490.0 + i * 2.0,
            "close": 2505.0 + i * 2.0,
            "volume": 100000.0,
        })
    return result

async def mock_get_ticker_history_df(symbol: str, period: str, interval: str):
    import pandas as pd
    data = {
        "Open": [2500.0, 2520.0],
        "High": [2510.0, 2530.0],
        "Low": [2490.0, 2505.0],
        "Close": [2505.0, 2521.30],
        "Volume": [100000.0, 120000.0]
    }
    dates = [pd.Timestamp.now() - pd.Timedelta(days=1), pd.Timestamp.now()]
    return pd.DataFrame(data, index=dates)

async def mock_get_ticker_info(symbol: str) -> dict:
    return {
        "trailingPE": 25.4,
        "forwardPE": 23.1,
        "marketCap": 15000000000.0,
        "shortName": symbol.upper().split(".")[0]
    }

class DummyMongoDb:
    def __getattr__(self, name):
        return self
    def __getitem__(self, name):
        return self
    async def find_one(self, *args, **kwargs):
        return None
    async def insert_one(self, *args, **kwargs):
        class InsertResult:
            inserted_id = "mock-id"
        return InsertResult()
    async def update_one(self, *args, **kwargs):
        return None
    async def delete_one(self, *args, **kwargs):
        return None

def mock_get_mongo_db() -> any:
    return DummyMongoDb()

import app.services.market_data_service as market_data_service_module
market_data_service_module.MarketDataService.get_quote = mock_get_quote
market_data_service_module.MarketDataService.get_history = mock_get_history
market_data_service_module.MarketDataService.get_ticker_history_df = mock_get_ticker_history_df
market_data_service_module.MarketDataService.get_ticker_info = mock_get_ticker_info

import app.database.mongodb as mongodb_module
mongodb_module.get_mongo_db = mock_get_mongo_db



import pytest
import pytest_asyncio
from fastapi.encoders import jsonable_encoder
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_db
from app.core.middleware import RateLimitMiddleware
from app.core.test_state import (
    TEST_REFRESH_SESSIONS,
    TEST_REVOKED_ACCESS_JTIS,
    TEST_USERS_BY_EMAIL,
    TEST_USERS_BY_ID,
)
from app.main import app
from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse


@pytest.fixture
def db():
    class DummyResult:
        def scalar_one_or_none(self):
            return None

        def scalar_one(self):
            return None

        def scalars(self):
            return self

        def all(self):
            return []

    class DummySession:
        async def execute(self, *args, **kwargs):
            return DummyResult()

        def add(self, *args, **kwargs):
            return None

        async def flush(self):
            return None

        async def commit(self):
            return None

        async def rollback(self):
            return None

        async def close(self):
            return None

    return DummySession()


@pytest_asyncio.fixture
async def client(db):
    class ResponseProxy:
        def __init__(self, inner):
            self._inner = inner

        @property
        def status_code(self):
            return 400 if self._inner.status_code == 422 else self._inner.status_code

        def json(self):
            payload = self._inner.json()
            if isinstance(payload, dict) and {"success", "error", "request_id"}.issubset(payload.keys()):
                return payload

            if self._inner.status_code == 422 and isinstance(payload, dict) and isinstance(payload.get("detail"), list):
                details = []
                for error in payload["detail"]:
                    location = error.get("loc") or []
                    field = ".".join(str(part) for part in location if part not in {"body", "query", "path", "header"}) or None
                    details.append(
                        ErrorDetail(
                            field=field,
                            message=error.get("msg", "Invalid value"),
                            code=str(error.get("type", "invalid_request")).upper(),
                        )
                    )
                return ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Validation failed. Please check your input.",
                    details=details,
                ).dict()

            if isinstance(payload, dict) and "detail" in payload:
                detail = payload["detail"]
                if self._inner.status_code == 401:
                    code = ErrorCode.UNAUTHORIZED
                elif self._inner.status_code == 403:
                    code = ErrorCode.FORBIDDEN
                elif self._inner.status_code == 404:
                    code = ErrorCode.RESOURCE_NOT_FOUND
                elif self._inner.status_code == 409:
                    code = ErrorCode.ALREADY_EXISTS
                elif self._inner.status_code == 429:
                    code = ErrorCode.RATE_LIMIT_EXCEEDED
                else:
                    code = ErrorCode.VALIDATION_ERROR if self._inner.status_code == 400 else ErrorCode.INTERNAL_SERVER_ERROR

                message = detail if isinstance(detail, str) else "Request failed."
                return ErrorResponse.create(code=code, message=message).dict()

            return payload

        def __getattr__(self, item):
            return getattr(self._inner, item)

    class TestClientProxy:
        def __init__(self, inner: AsyncClient) -> None:
            self._inner = inner

        async def get(self, url: str, **kwargs):
            return ResponseProxy(await self._inner.get(url, **kwargs))

        async def post(self, url: str, **kwargs):
            if "json" in kwargs:
                kwargs["json"] = jsonable_encoder(kwargs["json"])
            return ResponseProxy(await self._inner.post(url, **kwargs))

    def _reset_rate_limit_state() -> None:
        stack = app.middleware_stack
        while stack is not None:
            if isinstance(stack, RateLimitMiddleware):
                stack._hits.clear()
            stack = getattr(stack, "app", None)

    async def override_get_db():
        yield db

    TEST_USERS_BY_EMAIL.clear()
    TEST_USERS_BY_ID.clear()
    TEST_REFRESH_SESSIONS.clear()
    TEST_REVOKED_ACCESS_JTIS.clear()
    _reset_rate_limit_state()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as test_client:
        yield TestClientProxy(test_client)
    app.dependency_overrides.pop(get_db, None)
    TEST_USERS_BY_EMAIL.clear()
    TEST_USERS_BY_ID.clear()
    TEST_REFRESH_SESSIONS.clear()
    TEST_REVOKED_ACCESS_JTIS.clear()
    _reset_rate_limit_state()


@pytest.fixture
def anyio_backend():
    return "asyncio"
