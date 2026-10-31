"""Tests for app.core.config.Settings.

Regression coverage for a real bug: RAZORPAY_WEBHOOK_SECRET was read by
app/api/v1/payments.py via getattr(settings, "RAZORPAY_WEBHOOK_SECRET",
"REPLACE_ME"), but Settings never declared that field. pydantic-settings
only loads env vars for fields declared on the model, so no operator-set
RAZORPAY_WEBHOOK_SECRET could ever reach the running app - the webhook
secret was permanently unconfigurable regardless of the environment.
"""

from app.core.config import Settings


def test_razorpay_webhook_secret_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "a_real_operator_configured_secret")
    # _env_file=None: isolate from whatever backend/.env actually exists on
    # disk in this environment (a developer's real, credential-filled file),
    # so this test's result depends only on the monkeypatched process env.
    settings = Settings(_env_file=None)
    assert settings.RAZORPAY_WEBHOOK_SECRET == "a_real_operator_configured_secret"


def test_razorpay_webhook_secret_defaults_to_a_detectable_placeholder(monkeypatch):
    monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET", raising=False)
    settings = Settings(_env_file=None)
    assert "replace_me" in settings.RAZORPAY_WEBHOOK_SECRET.lower()


def test_supabase_and_sendgrid_key_fallbacks(monkeypatch):
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://avizvhsyqyrtyszgfjiv.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_service_role_jwt")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_key")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test_key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "noreply@neuroquant.local")

    settings = Settings(_env_file=None)
    assert settings.SUPABASE_SECRET_KEY == "test_service_role_jwt"
    assert settings.SUPABASE_ANON_KEY == "sb_publishable_test_key"
    assert (
        settings.SUPABASE_JWKS_URL
        == "https://avizvhsyqyrtyszgfjiv.supabase.co/auth/v1/.well-known/jwks.json"
    )
    assert settings.SENDGRID_FROM_EMAIL == "neuroquant990@gmail.com"


def test_production_rejects_localhost_redis(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://nq_api:secret@example.test/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        Settings(_env_file=None)
    except ValueError as exc:
        assert "REDIS_URL" in str(exc)
    else:
        raise AssertionError("production must reject process-local Redis")


def test_live_order_execution_is_fail_closed(monkeypatch):
    monkeypatch.setenv("LIVE_ORDER_EXECUTION_ENABLED", "true")

    try:
        Settings(_env_file=None)
    except ValueError as exc:
        assert "LIVE_ORDER_EXECUTION_ENABLED" in str(exc)
    else:
        raise AssertionError("live order execution must remain disabled")


def test_only_paper_trading_mode_is_supported(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_ONLY", "false")

    try:
        Settings(_env_file=None)
    except ValueError as exc:
        assert "PAPER_TRADING_ONLY" in str(exc)
    else:
        raise AssertionError("unsupported trading mode must be rejected")


def test_empty_bool_environment_variables(monkeypatch):
    monkeypatch.setenv("UPSTOX_ENABLED", "")
    monkeypatch.setenv("ALERT_EMAIL_ENABLED", "")
    monkeypatch.setenv("DEBUG", "")
    settings = Settings()
    assert settings.UPSTOX_ENABLED is False
    assert settings.ALERT_EMAIL_ENABLED is False
    assert settings.DEBUG is False

