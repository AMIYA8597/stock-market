"""Unit tests for the Supabase "email not confirmed" detector in auth.py."""

import httpx

from app.api.v1.auth import _is_email_not_confirmed


def _resp(status: int, body) -> httpx.Response:
    return httpx.Response(status, json=body)


def test_email_not_confirmed_by_error_code() -> None:
    assert _is_email_not_confirmed(
        _resp(400, {"code": 400, "error_code": "email_not_confirmed", "msg": "Email not confirmed"})
    )


def test_email_not_confirmed_by_legacy_description() -> None:
    assert _is_email_not_confirmed(
        _resp(400, {"error": "invalid_grant", "error_description": "Email not confirmed"})
    )


def test_wrong_password_is_not_email_not_confirmed() -> None:
    assert not _is_email_not_confirmed(
        _resp(400, {"error": "invalid_grant", "error_description": "Invalid login credentials"})
    )


def test_non_json_body_is_not_email_not_confirmed() -> None:
    assert not _is_email_not_confirmed(httpx.Response(502, text="<html>Bad Gateway</html>"))
