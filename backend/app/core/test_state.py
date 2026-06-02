from __future__ import annotations

import os

TEST_USERS_BY_EMAIL: dict[str, dict[str, object]] = {}
TEST_USERS_BY_ID: dict[str, dict[str, object]] = {}
TEST_REFRESH_SESSIONS: dict[str, dict[str, object]] = {}
TEST_REVOKED_ACCESS_JTIS: set[str] = set()
_LAST_TEST_ID: str | None = None


def is_test_mode() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def reset_test_state() -> None:
    TEST_USERS_BY_EMAIL.clear()
    TEST_USERS_BY_ID.clear()
    TEST_REFRESH_SESSIONS.clear()
    TEST_REVOKED_ACCESS_JTIS.clear()


def ensure_test_isolation() -> None:
    global _LAST_TEST_ID

    current_test_id = os.getenv("PYTEST_CURRENT_TEST")
    if not current_test_id:
        return

    if current_test_id != _LAST_TEST_ID:
        reset_test_state()
        _LAST_TEST_ID = current_test_id
