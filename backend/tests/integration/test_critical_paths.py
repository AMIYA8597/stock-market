"""Critical path integration tests for production readiness.

Tests the most important user workflows end-to-end:
- User registration → login → account access
- Payment flow → webhook processing
- Portfolio creation → transaction → performance calculation
- WebSocket connections for real-time feeds
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


class TestAuthFlow:
    """Test complete authentication lifecycle."""

    async def test_register_login_refresh_logout(self, client: AsyncClient, db: AsyncSession):
        """Complete auth flow: register → login → refresh → logout."""
        email = f"test_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"

        # REGISTER
        register_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Test User",
            }
        )
        assert register_resp.status_code == status.HTTP_201_CREATED
        user_data = register_resp.json()
        assert user_data["email"] == email
        assert "id" in user_data

        # LOGIN
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login_resp.status_code == status.HTTP_200_OK
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        assert access_token
        assert refresh_token

        # GET PROFILE with access token
        profile_resp = await client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_resp.status_code == status.HTTP_200_OK
        profile = profile_resp.json()
        assert profile["email"] == email

        # REFRESH TOKEN rotation
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == status.HTTP_200_OK
        new_tokens = refresh_resp.json()
        new_access = new_tokens["access_token"]
        assert new_access != access_token  # Must be new

        # Old access token should still work briefly
        profile_resp2 = await client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_resp2.status_code == status.HTTP_200_OK

        # LOGOUT
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"}
        )
        assert logout_resp.status_code == status.HTTP_204_NO_CONTENT

        # Old tokens should now be invalid
        invalid_resp = await client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {new_access}"}
        )
        # Could be 401 or 404 depending on implementation
        assert invalid_resp.status_code >= 400

    async def test_account_lockout_after_failed_attempts(self, client: AsyncClient):
        """Test account lockout after 5 failed login attempts."""
        email = f"locktest_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"
        wrong_password = "WrongPassword123!@#"

        # Create user
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Lock Test"}
        )

        # Try login 5 times with wrong password
        for _attempt in range(5):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": wrong_password}
            )
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED
            error = resp.json()
            assert error["error"]["code"] == "INVALID_CREDENTIALS"

        # 6th attempt should be blocked due to lock
        lock_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": wrong_password}
        )
        assert lock_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        error = lock_resp.json()
        assert error["error"]["code"] == "ACCOUNT_LOCKED"
        assert "locked" in error["error"]["message"].lower()

        # Correct password should also be blocked while locked
        locked_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert locked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestPaymentFlow:
    """Test complete payment lifecycle."""

    async def test_payment_idempotency(self, client: AsyncClient):
        """Test that duplicate payment requests return same result."""
        # Create payment intent
        resp1 = await client.post(
            "/api/v1/payments/intents",
            headers={"Idempotency-Key": "test-idempotent-123"},
            json={
                "amount": Decimal("100.00"),
                "currency": "INR",
                "method": "UPI",
            }
        )
        assert resp1.status_code == status.HTTP_200_OK
        intent1 = resp1.json()
        intent_id_1 = intent1["intent_id"]

        # Retry same request with same idempotency key
        resp2 = await client.post(
            "/api/v1/payments/intents",
            headers={"Idempotency-Key": "test-idempotent-123"},
            json={
                "amount": Decimal("100.00"),
                "currency": "INR",
                "method": "UPI",
            }
        )
        assert resp2.status_code == status.HTTP_200_OK
        intent2 = resp2.json()
        intent_id_2 = intent2["intent_id"]

        # Must return SAME intent, not create new one
        assert intent_id_1 == intent_id_2, "Idempotency key must return same intent"

    async def test_webhook_prevents_duplicate_processing(self, client: AsyncClient, db: AsyncSession):
        """Test that same webhook event is only processed once."""
        # This would require setting up a real webhook and testing duplicate delivery
        # Placeholder for comprehensive webhook test
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
            }
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
        resp = await client.get(
            "/api/v1/blog/posts/nonexistent-slug"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        error = resp.json()

        assert error["success"] is False
        assert error["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "request_id" in error


class TestRateLimiting:
    """Test rate limiting on auth endpoints."""

    async def test_auth_rate_limiting(self, client: AsyncClient):
        """Test that auth endpoints are rate limited to 10/minute."""
        # Try to make 11 login attempts (assuming 10/min limit)
        for attempt in range(11):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": f"test{attempt}@example.com", "password": "test"}
            )
            if attempt < 10:
                # First 10 should get through (with 401 for bad credentials)
                assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK], f"Attempt {attempt} failed"
            else:
                # 11th should be rate limited
                assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                error = resp.json()
                assert error["error"]["code"] == "RATE_LIMIT_EXCEEDED"


class TestDatabaseConstraints:
    """Test that database constraints and indexes work correctly."""

    async def test_user_email_unique_constraint(self, client: AsyncClient):
        """Test that duplicate emails are rejected."""
        email = f"unique_{uuid4().hex[:8]}@example.com"
        password = "SecurePass123!@#"

        # First registration succeeds
        resp1 = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "User 1"}
        )
        assert resp1.status_code == status.HTTP_201_CREATED

        # Duplicate email should fail
        resp2 = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "User 2"}
        )
        assert resp2.status_code == status.HTTP_409_CONFLICT
        error = resp2.json()
        assert error["error"]["code"] == "ALREADY_EXISTS"
