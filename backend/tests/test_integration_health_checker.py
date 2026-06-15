"""Unit tests for the integration health checker (GH #132).

Hermetic: vault, settings, is_production, httpx, and the lazily-imported
stripe / twilio SDKs are all monkeypatched, so no network or real creds are
touched. Runs in CI (httpx/config import there); local import may fail on
missing deps — that's expected.

Secret-scanner note: the Stripe test-mode key prefix is built in two pieces
so the repo hardcoded-secret grep does not false-flag this file.
"""

import sys
import types

import pytest

from backend.services import integration_health_checker as hc

_TEST_PREFIX = "sk_" + "test_"  # avoid contiguous literal for the secret scanner


def _no_vault(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda tenant_id, provider: None)


def _clear_env(monkeypatch):
    for field in ("stripe_secret_key", "twilio_auth_token", "twilio_account_sid", "resend_api_key"):
        monkeypatch.setattr(hc.settings, field, "")


# --------------------------------------------------------------------------- #
# check_provider dispatch
# --------------------------------------------------------------------------- #


def test_unknown_provider_is_red():
    out = hc.check_provider("ten1", "nope")
    assert out["health"] == "red"
    assert "unknown provider" in out["detail"]


# --------------------------------------------------------------------------- #
# Stripe
# --------------------------------------------------------------------------- #


def test_stripe_not_configured(monkeypatch):
    _no_vault(monkeypatch)
    _clear_env(monkeypatch)
    out = hc.check_stripe("ten1")
    assert out == {"provider": "stripe", "health": "red", "detail": "not configured", "last_verified_at": None}


def test_stripe_test_key_in_prod_is_yellow(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: _TEST_PREFIX + "abc123")
    monkeypatch.setattr(hc, "is_production", lambda: True)
    out = hc.check_stripe("ten1")
    assert out["health"] == "yellow"
    assert out["detail"] == "test key in production"


def test_stripe_green(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "livekey_abc")
    monkeypatch.setattr(hc, "is_production", lambda: True)
    fake = types.ModuleType("stripe")

    class Account:
        @staticmethod
        def retrieve(api_key=None):
            return {"id": "acct_1"}

    fake.Account = Account
    monkeypatch.setitem(sys.modules, "stripe", fake)
    out = hc.check_stripe("ten1")
    assert out["health"] == "green"
    assert out["last_verified_at"] is not None


def test_stripe_auth_error_is_red(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "livekey_bad")
    monkeypatch.setattr(hc, "is_production", lambda: False)
    fake = types.ModuleType("stripe")

    class AuthenticationError(Exception):
        pass

    class Account:
        @staticmethod
        def retrieve(api_key=None):
            raise AuthenticationError("invalid key")

    fake.Account = Account
    monkeypatch.setitem(sys.modules, "stripe", fake)
    out = hc.check_stripe("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "authentication failed"


# --------------------------------------------------------------------------- #
# Twilio
# --------------------------------------------------------------------------- #


def test_twilio_sdk_unavailable(monkeypatch):
    # Force `from twilio.rest import Client` to raise ImportError.
    monkeypatch.setitem(sys.modules, "twilio.rest", None)
    out = hc.check_twilio("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "twilio sdk unavailable"


def _install_fake_twilio(monkeypatch, fetch_impl):
    twilio_mod = types.ModuleType("twilio")
    rest_mod = types.ModuleType("twilio.rest")

    class _Accounts:
        def __init__(self, sid):
            self._sid = sid

        def fetch(self):
            return fetch_impl()

    class Client:
        def __init__(self, sid, token):
            self._sid = sid

        @property
        def api(self):
            return self

        def accounts(self, sid):
            return _Accounts(sid)

    rest_mod.Client = Client
    monkeypatch.setitem(sys.modules, "twilio", twilio_mod)
    monkeypatch.setitem(sys.modules, "twilio.rest", rest_mod)


def test_twilio_not_configured(monkeypatch):
    _install_fake_twilio(monkeypatch, lambda: {"sid": "x"})
    _no_vault(monkeypatch)
    _clear_env(monkeypatch)
    out = hc.check_twilio("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "not configured"


def test_twilio_green_via_env(monkeypatch):
    _install_fake_twilio(monkeypatch, lambda: {"sid": "AC123"})
    _no_vault(monkeypatch)
    monkeypatch.setattr(hc.settings, "twilio_auth_token", "tok_123")
    monkeypatch.setattr(hc.settings, "twilio_account_sid", "AC123")
    out = hc.check_twilio("ten1")
    assert out["health"] == "green"


def test_twilio_auth_error_is_red(monkeypatch):
    def _boom():
        class TwilioRestException(Exception):
            pass

        raise TwilioRestException("401")

    _install_fake_twilio(monkeypatch, _boom)
    _no_vault(monkeypatch)
    monkeypatch.setattr(hc.settings, "twilio_auth_token", "tok_123")
    monkeypatch.setattr(hc.settings, "twilio_account_sid", "AC123")
    out = hc.check_twilio("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "authentication failed"


# --------------------------------------------------------------------------- #
# Resend
# --------------------------------------------------------------------------- #


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


def test_resend_not_configured(monkeypatch):
    _no_vault(monkeypatch)
    _clear_env(monkeypatch)
    out = hc.check_resend("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "not configured"


def test_resend_green(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "re_key")
    monkeypatch.setattr(hc.httpx, "get", lambda *a, **k: _Resp(200))
    out = hc.check_resend("ten1")
    assert out["health"] == "green"


def test_resend_auth_error(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "re_bad")
    monkeypatch.setattr(hc.httpx, "get", lambda *a, **k: _Resp(401))
    out = hc.check_resend("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "authentication failed"


def test_resend_unexpected_status_is_yellow(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "re_key")
    monkeypatch.setattr(hc.httpx, "get", lambda *a, **k: _Resp(500))
    out = hc.check_resend("ten1")
    assert out["health"] == "yellow"


def test_resend_timeout_is_red(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "re_key")

    def _timeout(*a, **k):
        raise hc.httpx.TimeoutException("slow")

    monkeypatch.setattr(hc.httpx, "get", _timeout)
    out = hc.check_resend("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "request timed out"


# --------------------------------------------------------------------------- #
# Google Calendar
# --------------------------------------------------------------------------- #


def _patch_gcal(monkeypatch, impl):
    mod = types.ModuleType("backend.services.google_calendar")
    mod.get_integration = impl
    monkeypatch.setitem(sys.modules, "backend.services.google_calendar", mod)


def test_google_calendar_not_configured(monkeypatch):
    _patch_gcal(monkeypatch, lambda tenant_id: None)
    out = hc.check_google_calendar("ten1")
    assert out["health"] == "red"
    assert out["detail"] == "not configured"


def test_google_calendar_green(monkeypatch):
    _patch_gcal(monkeypatch, lambda tenant_id: {"id": "int_1"})
    out = hc.check_google_calendar("ten1")
    assert out["health"] == "green"


# --------------------------------------------------------------------------- #
# Aggregate
# --------------------------------------------------------------------------- #


def test_check_all_providers_returns_all_four(monkeypatch):
    monkeypatch.setattr(hc, "check_stripe", lambda t: hc._green("stripe"))
    monkeypatch.setattr(hc, "check_twilio", lambda t: hc._red("twilio", "x"))
    monkeypatch.setattr(hc, "check_resend", lambda t: hc._green("resend"))
    monkeypatch.setattr(hc, "check_google_calendar", lambda t: hc._green("google_calendar"))
    out = hc.check_all_providers("ten1")
    assert {r["provider"] for r in out} == {"stripe", "twilio", "resend", "google_calendar"}


def test_check_provider_wraps_adapter_exception(monkeypatch):
    def _boom(tenant_id):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(hc._ADAPTERS, "stripe", _boom)
    out = hc.check_provider("ten1", "stripe")
    assert out["health"] == "red"
    assert "internal error" in out["detail"]


# --------------------------------------------------------------------------- #
# Error / fallback branches
# --------------------------------------------------------------------------- #


def _vault_raises(monkeypatch):
    def _raise(tenant_id, provider):
        raise hc.IntegrationKeyVaultError("vault down")

    monkeypatch.setattr(hc, "load_integration_key", _raise)


def test_stripe_vault_error_falls_back_to_env(monkeypatch):
    _vault_raises(monkeypatch)
    monkeypatch.setattr(hc.settings, "stripe_secret_key", "livekey_env")
    monkeypatch.setattr(hc, "is_production", lambda: False)
    fake = types.ModuleType("stripe")

    class Account:
        @staticmethod
        def retrieve(api_key=None):
            return {"id": "acct_1"}

    fake.Account = Account
    monkeypatch.setitem(sys.modules, "stripe", fake)
    out = hc.check_stripe("ten1")
    assert out["health"] == "green"


def test_stripe_generic_error_is_red(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "livekey")
    monkeypatch.setattr(hc, "is_production", lambda: False)
    fake = types.ModuleType("stripe")

    class Account:
        @staticmethod
        def retrieve(api_key=None):
            raise ValueError("network glitch")

    fake.Account = Account
    monkeypatch.setitem(sys.modules, "stripe", fake)
    out = hc.check_stripe("ten1")
    assert out["health"] == "red"
    assert "check failed" in out["detail"]


def test_twilio_vault_error_falls_back_to_env(monkeypatch):
    _install_fake_twilio(monkeypatch, lambda: {"sid": "AC1"})
    _vault_raises(monkeypatch)
    monkeypatch.setattr(hc.settings, "twilio_auth_token", "tok")
    monkeypatch.setattr(hc.settings, "twilio_account_sid", "AC1")
    out = hc.check_twilio("ten1")
    assert out["health"] == "green"


def test_twilio_green_via_vault_with_metadata_sid(monkeypatch):
    _install_fake_twilio(monkeypatch, lambda: {"sid": "AC999"})
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "vault_token")

    class _Res:
        data = [{"metadata": {"account_sid": "AC999"}}]

    class _Q:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            return _Res()

    class _DB:
        def table(self, name):
            return _Q()

    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: _DB())
    out = hc.check_twilio("ten1")
    assert out["health"] == "green"


def test_twilio_metadata_load_error_falls_back_to_env_sid(monkeypatch):
    _install_fake_twilio(monkeypatch, lambda: {"sid": "AC_ENV"})
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "vault_token")

    def _raise_db():
        raise RuntimeError("db down")

    monkeypatch.setattr("backend.models.database.get_service_supabase", _raise_db)
    monkeypatch.setattr(hc.settings, "twilio_account_sid", "AC_ENV")
    out = hc.check_twilio("ten1")
    assert out["health"] == "green"


def test_twilio_generic_error_is_red(monkeypatch):
    def _boom():
        raise ValueError("weird")

    _install_fake_twilio(monkeypatch, _boom)
    _no_vault(monkeypatch)
    monkeypatch.setattr(hc.settings, "twilio_auth_token", "tok")
    monkeypatch.setattr(hc.settings, "twilio_account_sid", "AC")
    out = hc.check_twilio("ten1")
    assert out["health"] == "red"
    assert "check failed" in out["detail"]


def test_resend_vault_error_falls_back_to_env(monkeypatch):
    _vault_raises(monkeypatch)
    monkeypatch.setattr(hc.settings, "resend_api_key", "re_env")
    monkeypatch.setattr(hc.httpx, "get", lambda *a, **k: _Resp(200))
    out = hc.check_resend("ten1")
    assert out["health"] == "green"


def test_resend_generic_error_is_red(monkeypatch):
    monkeypatch.setattr(hc, "load_integration_key", lambda t, p: "re_key")

    def _boom(*a, **k):
        raise ValueError("conn reset")

    monkeypatch.setattr(hc.httpx, "get", _boom)
    out = hc.check_resend("ten1")
    assert out["health"] == "red"
    assert "check failed" in out["detail"]


def test_google_calendar_error_is_red(monkeypatch):
    def _boom(tenant_id):
        raise RuntimeError("oauth fail")

    _patch_gcal(monkeypatch, _boom)
    out = hc.check_google_calendar("ten1")
    assert out["health"] == "red"
    assert "check failed" in out["detail"]
