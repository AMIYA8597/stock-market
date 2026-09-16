import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_auth_lifecycle(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    # Mock email sending
    async def mock_enqueue_email(*args, **kwargs):
        return True

    monkeypatch.setattr("app.api.v1.auth.enqueue_email", mock_enqueue_email)

    # Mock DB specifically for this test
    mock_db = {}

    async def mock_execute(stmt, *args, **kwargs):
        class MockResult:
            def scalar_one_or_none(self):
                # Basic mock for select(User).where(User.email == email)
                for user in mock_db.values():
                    # Return the first user (we only have one in this test)
                    return user
                return None

        return MockResult()

    def mock_add(obj):
        if hasattr(obj, "email"):
            mock_db[obj.email] = obj
            obj.id = uuid.uuid4()
            obj.created_at = "2026-07-22T00:00:00Z"

    async def mock_refresh(user):
        pass

    monkeypatch.setattr(db, "execute", mock_execute)
    monkeypatch.setattr(db, "add", mock_add)
    monkeypatch.setattr(db, "refresh", mock_refresh, raising=False)

    # 1. Register
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    password = "StrongPassword123!"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg_res.status_code == 201

    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # 3. Call protected route with token
    me_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 4. Refresh
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens

    # 5. 401 without token
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401


async def test_entitlement_gating(client: AsyncClient, db: AsyncSession):
    # Need to test require_active_subscription(tier)
    # The actual gating logic requires a plan.
    pass
