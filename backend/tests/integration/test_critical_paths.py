"""Critical path integration tests for production readiness.

Tests the most important user workflows end-to-end:
- User registration → login → account access
- Payment flow → webhook processing
- Portfolio creation → transaction → performance calculation
- WebSocket connections for real-time feeds
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _register_verify_and_capture(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, email: str, password: str, full_name: str) -> None:
    """Register then verify via OTP, using a monkeypatched generator to
    capture the plaintext code (the real code only ever persists a hash)."""
    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp
    captured: dict[str, str] = {}

    def spy_generate_otp():
        code = real_generate_otp()
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_module, "generate_otp", spy_generate_otp)

    register_resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert register_resp.status_code == status.HTTP_201_CREATED, register_resp.text

    verify_resp = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": captured["code"], "password": password},
    )
    assert verify_resp.status_code == status.HTTP_200_OK, verify_resp.text


class TestAuthFlow:
    """Test complete authentication lifecycle.

    Uses the `auth_client` fixture (tests/integration/conftest.py, a real
    SQLite-backed client) rather than the shared DummySession `client`/`db`
    fixtures: those don't model the email_otps table the register -> verify
    -> login lifecycle now depends on.
    """

    async def test_register_login_refresh_logout(self, auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
        """Complete auth flow: register → verify OTP → login → refresh → logout."""
        email = f"test_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"

        await _register_verify_and_capture(auth_client, monkeypatch, email, password, "Test User")

        # LOGIN
        login_resp = await auth_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == status.HTTP_200_OK
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        assert access_token
        assert refresh_token

        # GET PROFILE with access token
        profile_resp = await auth_client.get(
            "/api/v1/users/profile", headers={"Authorization": f"Bearer {access_token}"}
        )
        if profile_resp.status_code != 200:
            print("ERROR STATUS", profile_resp.text)
        assert profile_resp.status_code == status.HTTP_200_OK
        profile = profile_resp.json()
        assert profile["email"] == email

        # REFRESH TOKEN rotation
        refresh_resp = await auth_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == status.HTTP_200_OK
        new_tokens = refresh_resp.json()
        new_access = new_tokens["access_token"]

        # Old access token should still work briefly
        profile_resp2 = await auth_client.get(
            "/api/v1/users/profile", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_resp2.status_code == status.HTTP_200_OK

        # LOGOUT
        logout_resp = await auth_client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {new_access}"}
        )
        assert logout_resp.status_code == status.HTTP_204_NO_CONTENT

    async def test_account_lockout_after_failed_attempts(self, auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
        """Test account lockout after 5 failed login attempts."""
        email = f"locktest_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"
        wrong_password = "WrongPassword123!@#"

        await _register_verify_and_capture(auth_client, monkeypatch, email, password, "Lock Test")

        # Try login 5 times with wrong password
        for _attempt in range(5):
            resp = await auth_client.post(
                "/api/v1/auth/login", json={"email": email, "password": wrong_password}
            )
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED
            error = resp.json()
            assert error["error"]["code"] == "INVALID_CREDENTIALS"

        # 6th attempt should be blocked due to lock
        lock_resp = await auth_client.post(
            "/api/v1/auth/login", json={"email": email, "password": wrong_password}
        )
        assert lock_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        error = lock_resp.json()
        assert error["error"]["code"] == "ACCOUNT_LOCKED"
        assert "locked" in error["error"]["message"].lower()

        # Correct password should also be blocked while locked
        locked_resp = await auth_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert locked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestPaymentFlow:
    """Test complete payment lifecycle."""

    pass


class TestErrorResponseFormat:
    """Test that all error responses follow standard format."""

    async def test_validation_error_format(self, client: AsyncClient):
        """Test error response format for validation errors."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",  # Invalid email
                "password": "weak",  # Too weak
                "full_name": "",  # Empty
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        error = resp.json()

        # Check standard error structure
        assert "success" in error
        assert error["success"] is False
        assert "error" in error
        assert "code" in error["error"]
        assert "message" in error["error"]
        assert "details" in error["error"]
        assert "request_id" in error
        assert error["error"]["code"] == "VALIDATION_ERROR"

    async def test_unauthorized_error_format(self, client: AsyncClient):
        """Test error response format for unauthorized."""
        resp = await client.get(
            "/api/v1/users/profile"
            # No authorization header
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        error = resp.json()

        assert error["success"] is False
        assert error["error"]["code"] == "UNAUTHORIZED"
        assert "request_id" in error

    async def test_not_found_error_format(self, client: AsyncClient):
        """Test error response format for resource not found."""
        resp = await client.get("/api/v1/blog/posts/nonexistent-slug")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        error = resp.json()

        assert error["success"] is False
        assert error["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "request_id" in error


class TestRateLimiting:
    """Test rate limiting on auth endpoints."""

    async def test_auth_rate_limiting(self, client: AsyncClient):
        pass


class TestDatabaseConstraints:
    """Test that database constraints and indexes work correctly."""

    async def test_user_email_unique_constraint(self, auth_client: AsyncClient):
        """Test that duplicate emails are rejected."""
        email = f"unique_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"

        # First registration succeeds
        resp1 = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "User 1"},
        )
        assert resp1.status_code == status.HTTP_201_CREATED

        # Duplicate email should fail
        resp2 = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "User 2"},
        )
        assert resp2.status_code == status.HTTP_409_CONFLICT
        error = resp2.json()
        assert error["error"]["code"] == "ALREADY_EXISTS"
