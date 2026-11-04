"""Sentry stays off without a DSN, and events lose PII before send."""

from backend.services import sentry_scrub


def test_empty_dsn_does_not_initialize(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("sentry_sdk.init must not run without a DSN")

    monkeypatch.setattr(
        "sentry_sdk.init",
        forbidden,
        raising=False,
    )
    assert sentry_scrub.init_sentry("") is False
    assert sentry_scrub.init_sentry("   ") is False


def test_dsn_initializes_with_scrubber_and_pii_off(monkeypatch):
    seen = {}

    def capture(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr("sentry_sdk.init", capture)
    monkeypatch.setattr(
        "sentry_sdk.integrations.fastapi.FastApiIntegration",
        lambda: "fastapi",
        raising=False,
    )
    monkeypatch.setattr(
        "sentry_sdk.integrations.starlette.StarletteIntegration",
        lambda: "starlette",
        raising=False,
    )
    assert sentry_scrub.init_sentry("https://public@example.ingest.sentry.io/1") is True
    assert seen["send_default_pii"] is False
    assert seen["before_send"] is sentry_scrub.scrub_sentry_event
    assert seen["before_breadcrumb"] is sentry_scrub.scrub_sentry_breadcrumb
    assert seen["dsn"].startswith("https://")


def test_scrubber_redacts_headers_user_and_exception_text():
    event = {
        "message": "failed for ada@example.com",
        "request": {
            "headers": {
                "Authorization": "Bearer secret-token",
                "Cookie": "session=abc",
                "User-Agent": "widget",
            },
            "cookies": {"session": "abc"},
            "data": {"email": "ada@example.com", "note": "call +1 (555) 010-1212"},
            "query_string": "email=ada@example.com",
        },
        "user": {"email": "ada@example.com", "ip_address": "203.0.113.8", "id": "t1"},
        "exception": {
            "values": [
                {"value": "provider said ada@example.com / +1 (555) 010-1212"},
            ]
        },
        "extra": {"owner_email": "ada@example.com"},
    }

    cleaned = sentry_scrub.scrub_sentry_event(event, {})

    assert cleaned["request"]["headers"]["Authorization"] == "[redacted]"
    assert cleaned["request"]["headers"]["Cookie"] == "[redacted]"
    assert cleaned["request"]["headers"]["User-Agent"] == "widget"
    assert "cookies" not in cleaned["request"]
    assert "data" not in cleaned["request"]
    assert "ada@example.com" not in cleaned["request"]["query_string"]
    assert cleaned["user"]["email"] == "[redacted]"
    assert cleaned["user"]["ip_address"] == "[redacted]"
    assert cleaned["user"]["id"] == "t1"
    assert "ada@example.com" not in cleaned["message"]
    assert "ada@example.com" not in cleaned["exception"]["values"][0]["value"]
    assert "555" not in cleaned["exception"]["values"][0]["value"]
    assert "ada@example.com" not in cleaned["extra"]["owner_email"]


def test_before_send_scrubs_breadcrumbs_and_logentry():
    event = {
        "breadcrumbs": {
            "values": [
                {
                    "message": "login ada@example.com with Bearer sk-live-secretvalue",
                    "data": {
                        "api_key": "sk-live-secretvalue",
                        "path": "/widget",
                        "note": "owner ada@example.com token=abc123secret",
                    },
                }
            ]
        },
        "logentry": {
            "message": "mail to ada@example.com failed",
            "formatted": "authorization=Bearer sk-live-secretvalue",
        },
    }

    cleaned = sentry_scrub.scrub_sentry_event(event, {})
    blob = str(cleaned["breadcrumbs"]) + str(cleaned["logentry"])
    assert "ada@example.com" not in blob
    assert "sk-live-secretvalue" not in blob
    assert "abc123secret" not in blob
    assert cleaned["breadcrumbs"]["values"][0]["data"]["api_key"] == "[redacted]"
    assert cleaned["breadcrumbs"]["values"][0]["data"]["path"] == "/widget"
    assert "[redacted-email]" in cleaned["logentry"]["message"]
    assert "[redacted-key]" in cleaned["logentry"]["formatted"]


def test_before_breadcrumb_scrubs_secrets_and_drops_non_dicts():
    crumb = sentry_scrub.scrub_sentry_breadcrumb(
        {
            "message": "ada@example.com",
            "data": {"password": "hunter2", "status": "ok"},
        },
        {},
    )
    assert crumb["data"]["password"] == "[redacted]"
    assert crumb["data"]["status"] == "ok"
    assert "ada@example.com" not in crumb["message"]
    assert sentry_scrub.scrub_sentry_breadcrumb("raw ada@example.com", {}) is None
