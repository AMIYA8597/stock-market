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
