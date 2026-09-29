"""Legacy compat check for the /auth/login alias, /auth/me, and /auth/logout.

Uses the shared `auth_client` fixture (tests/integration/conftest.py) - a
real SQLite-backed client - rather than the shared DummySession fixture in
tests/conftest.py: that mock only recognizes a handful of hardcoded query
shapes (users, refresh_sessions) and has no concept of the email_otps table
the real register->verify->login lifecycle now depends on. See
tests/integration/test_auth.py for the full lifecycle coverage this file
only needs a thin compat slice of.
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_auth_login_alias_and_profile_logout(auth_client: AsyncClient) -> None:
    email = f"trader_{uuid.uuid4().hex[:8]}@example.com"
    password = "S3curePass!123XY"

    register = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Trader"},
    )
    assert register.status_code == 201, register.text

    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp
    captured: dict[str, str] = {}

    def spy():
        code = real_generate_otp()
        captured["code"] = code
        return code

    # register already ran, so re-issue a fresh OTP we can actually capture.
    otp_module.generate_otp = spy
    try:
        resend = await auth_client.post("/api/v1/auth/resend-otp", json={"email": email, "purpose": "signup"})
        assert resend.status_code == 202
    finally:
        otp_module.generate_otp = real_generate_otp

    verify = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": captured["code"], "password": password},
    )
    assert verify.status_code == 200, verify.text

    login = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token_payload = login.json()
    assert "access_token" in token_payload

    me = await auth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_payload['access_token']}"}
    )
    assert me.status_code == 200
    me_payload = me.json()
    assert "email" in me_payload

    logout = await auth_client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token_payload['access_token']}"}
    )
    assert logout.status_code in (200, 204)
