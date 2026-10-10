"""Upstox routes live under a single /auth prefix (plus the legacy alias)."""

from app.api.v1.auth import router as auth_router


def test_upstox_routes_have_single_auth_prefix_and_legacy_alias() -> None:
    paths = {route.path for route in auth_router.routes}
    for name in ("login-url", "status", "callback"):
        # Correct path, which the frontend and the UPSTOX_REDIRECT_URI default use.
        assert f"/auth/upstox/{name}" in paths
        # Legacy double-prefixed path kept so existing links keep working.
        assert f"/auth/auth/upstox/{name}" in paths
