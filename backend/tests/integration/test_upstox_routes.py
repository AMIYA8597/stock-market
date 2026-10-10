"""Upstox route wiring: correct /auth prefix, legacy alias, and auth check."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_upstox_status_requires_login(auth_client: AsyncClient):
    # The response includes the connected broker account's profile, so it
    # must not be readable anonymously - on the fixed path or the legacy one.
    for path in ("/api/v1/auth/upstox/status", "/api/v1/auth/auth/upstox/status"):
        resp = await auth_client.get(path)
        assert resp.status_code == 401, (path, resp.text)
