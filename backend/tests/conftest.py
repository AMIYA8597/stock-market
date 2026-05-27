"""Pytest bootstrap for backend package imports."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.encoders import jsonable_encoder
from httpx import ASGITransport, AsyncClient

# Ensure backend root is importable as top-level packages: app, research, tests.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

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
