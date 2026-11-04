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
