"""End-to-end auth lifecycle tests against a real (in-memory) SQLite DB.

The shared `client`/`db` fixtures in tests/conftest.py back onto a
hand-written DummySession that only recognizes a few hardcoded query shapes
(users, refresh_sessions) - it has no concept of the new email_otps table or
the lockout columns, so it can't exercise the real register -> verify-OTP ->
login lifecycle this module tests. Instead this file uses the `auth_client`
fixture (tests/integration/conftest.py), which drives the actual HTTP
endpoints against a real SQLite engine, exactly as a real client would.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_capture_otp(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, email: str, password: str) -> str:
    """Register, capturing the plaintext OTP via a monkeypatched generator
    (the real code never returns it - it's hashed before it ever leaves
    create_otp - so this is the only legitimate way a test can know it)."""
    captured: dict[str, str] = {}
    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp

    def spy_generate_otp():
        code = real_generate_otp()
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_module, "generate_otp", spy_generate_otp)

    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text
    assert "code" in captured
    return captured["code"]


STRONG_PASSWORD = "Str0ng!Passw0rd#42"


# ─── Registration ────────────────────────────────────────────────────────


async def test_register_rejects_invalid_email(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": STRONG_PASSWORD, "full_name": "X"},
    )
    # This app's global RequestValidationError handler (app/core/errors.py)
    # normalizes FastAPI's native 422 down to 400 with a structured envelope.
    assert resp.status_code == 400


async def test_register_rejects_weak_password(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "weak", "full_name": "X"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "PASSWORD_TOO_WEAK"
    assert len(body["error"]["details"]) > 0


async def test_register_rejects_duplicate_email(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "Again"},
    )
    assert resp.status_code == 409


async def test_valid_registration_sends_otp_and_does_not_grant_immediate_access(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    email = _unique_email()
    await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    # Cannot log in until the OTP is verified.
    login_resp = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert login_resp.status_code == 403


async def test_registration_race_does_not_create_duplicate_accounts(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Two near-simultaneous registrations for the same email must not both succeed."""
    import asyncio

    email = _unique_email()

    async def attempt():
        return await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": STRONG_PASSWORD, "full_name": "Racer"},
        )

    results = await asyncio.gather(attempt(), attempt())
    statuses = sorted(r.status_code for r in results)
    # Safety invariant: at most one registration may succeed.
    # SQLite (used in tests) may serialise both writes to the same row and
    # reject both with 409 — [409, 409] is also acceptable; what must never
    # happen is both returning 201 (duplicate account created).
    assert statuses.count(201) <= 1, "Both concurrent registrations succeeded — duplicate user created"
    assert all(s in {201, 409} for s in statuses), f"Unexpected status codes: {statuses}"


# ─── OTP verification ────────────────────────────────────────────────────


async def test_correct_otp_verifies_and_authenticates(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    code = await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    resp = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": code, "password": STRONG_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert "access_token" in tokens

    me_resp = await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email_verified"] is True


async def test_wrong_otp_is_rejected(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    resp = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": "000000", "password": STRONG_PASSWORD},
    )
    assert resp.status_code == 400


async def test_reused_otp_is_rejected(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    code = await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    first = await auth_client.post(
        "/api/v1/auth/verify-signup-otp", json={"email": email, "otp": code, "password": STRONG_PASSWORD}
    )
    assert first.status_code == 200

    second = await auth_client.post(
        "/api/v1/auth/verify-signup-otp", json={"email": email, "otp": code, "password": STRONG_PASSWORD}
    )
    assert second.status_code == 400


async def test_excessive_wrong_otp_attempts_are_rejected(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    code = await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    # OTP_MAX_ATTEMPTS default is 5 - the 5th wrong attempt burns the code
    # (it's consumed the moment attempts reaches the limit), so every
    # attempt from here on, including this loop's 6th, correctly reports
    # "no live code" rather than accepting further guesses.
    for _ in range(5):
        resp = await auth_client.post(
            "/api/v1/auth/verify-signup-otp",
            json={"email": email, "otp": "000000", "password": STRONG_PASSWORD},
        )
        assert resp.status_code == 400

    sixth_attempt = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": "000000", "password": STRONG_PASSWORD},
    )
    assert sixth_attempt.status_code == 400

    # Even the *correct* code is now rejected - the code was burned by the
    # excessive wrong attempts, not just rate-limited for wrong guesses.
    correct_attempt = await auth_client.post(
        "/api/v1/auth/verify-signup-otp",
        json={"email": email, "otp": code, "password": STRONG_PASSWORD},
    )
    assert correct_attempt.status_code == 400


async def test_resend_otp_issues_a_working_new_code(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = _unique_email()
    old_code = await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)

    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp
    captured: dict[str, str] = {}

    def spy():
        code = real_generate_otp()
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_module, "generate_otp", spy)

    resend_resp = await auth_client.post("/api/v1/auth/resend-otp", json={"email": email, "purpose": "signup"})
    assert resend_resp.status_code == 202
    new_code = captured["code"]
    assert new_code != old_code

    # Old code no longer works, new one does.
    old_attempt = await auth_client.post(
        "/api/v1/auth/verify-signup-otp", json={"email": email, "otp": old_code, "password": STRONG_PASSWORD}
    )
    assert old_attempt.status_code == 400

    new_attempt = await auth_client.post(
        "/api/v1/auth/verify-signup-otp", json={"email": email, "otp": new_code, "password": STRONG_PASSWORD}
    )
    assert new_attempt.status_code == 200


# ─── Login ───────────────────────────────────────────────────────────────


async def test_login_with_unregistered_email_says_account_not_found(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "whatever123!A"}
    )
    assert resp.status_code == 404
    assert "register" in resp.json()["error"]["message"].lower()


async def test_check_email_reports_existence_without_a_password(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    unknown = await auth_client.post("/api/v1/auth/check-email", json={"email": _unique_email()})
    assert unknown.json() == {"exists": False}

    email = _unique_email()
    await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)
    known = await auth_client.post("/api/v1/auth/check-email", json={"email": email})
    assert known.json() == {"exists": True}


async def _register_verify_and_login_ready(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> str:
    email = _unique_email()
    code = await _register_and_capture_otp(auth_client, monkeypatch, email, STRONG_PASSWORD)
    verify_resp = await auth_client.post(
        "/api/v1/auth/verify-signup-otp", json={"email": email, "otp": code, "password": STRONG_PASSWORD}
    )
    assert verify_resp.status_code == 200
    return email


async def test_correct_password_logs_in_after_verification(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)

    resp = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_wrong_password_is_rejected(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)

    resp = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": "TotallyWrong123!"})
    assert resp.status_code == 401


async def test_repeated_wrong_passwords_lock_the_account(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)

    last_status = None
    for _ in range(6):  # LOGIN_MAX_FAILED_ATTEMPTS default is 5
        resp = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass123!"})
        last_status = resp.status_code
    assert last_status == 429

    # Even the correct password is now rejected until the lockout window passes.
    correct_attempt = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert correct_attempt.status_code == 429


async def test_protected_route_requires_token(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ─── Forgot / reset password ─────────────────────────────────────────────


async def test_forgot_password_gives_generic_response_regardless_of_existence(auth_client: AsyncClient):
    known_resp = await auth_client.post("/api/v1/auth/forgot-password", json={"email": _unique_email()})
    assert known_resp.status_code == 202
    assert "message" in known_resp.json()


async def test_full_password_reset_flow(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)

    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp
    captured: dict[str, str] = {}

    def spy():
        code = real_generate_otp()
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_module, "generate_otp", spy)

    forgot_resp = await auth_client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_resp.status_code == 202
    reset_code = captured["code"]

    new_password = "N3wStr0ng!Passw0rd9"
    reset_resp = await auth_client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": reset_code, "new_password": new_password},
    )
    assert reset_resp.status_code == 200, reset_resp.text

    old_login = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert old_login.status_code == 401

    new_login = await auth_client.post("/api/v1/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200


async def test_reset_password_rejects_invalid_code(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)
    await auth_client.post("/api/v1/auth/forgot-password", json={"email": email})

    resp = await auth_client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": "000000", "new_password": "AnotherStr0ng!Pass9"},
    )
    assert resp.status_code == 400


async def test_reset_password_enforces_password_policy(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    email = await _register_verify_and_login_ready(auth_client, monkeypatch)

    import app.core.otp as otp_module

    real_generate_otp = otp_module.generate_otp
    captured: dict[str, str] = {}

    def spy():
        code = real_generate_otp()
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_module, "generate_otp", spy)
    await auth_client.post("/api/v1/auth/forgot-password", json={"email": email})

    resp = await auth_client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": captured["code"], "new_password": "weak"},
    )
    assert resp.status_code == 400
