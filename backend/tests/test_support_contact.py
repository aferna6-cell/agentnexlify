"""Tests for the public support contact endpoint (routers/support.py).

Calls the route coroutine directly with the limiter disabled and a dummy
request. Verifies persist + email on the happy path, that a DB failure still
returns success (best-effort), the admin-email no-op/Resend paths, and email
validation.
"""

import asyncio
import sys
import types

import pytest
from pydantic import ValidationError

import backend.routers.support as sup
from backend.models.schemas import ContactRequest


def _payload(**kw):
    base = {"name": "Jane", "email": "jane@example.com", "subject": "Hi", "message": "hello"}
    base.update(kw)
    return ContactRequest(**base)


class _DB:
    def __init__(self):
        self.inserted = []

    def table(self, name):
        return self

    def insert(self, row):
        self.inserted.append(row)
        return self

    def execute(self):
        return None


def test_submit_contact_persists_and_emails(monkeypatch):
    monkeypatch.setattr(sup.limiter, "enabled", False)
    db = _DB()
    monkeypatch.setattr(sup, "get_service_supabase", lambda: db)
    sent = {}
    monkeypatch.setattr(sup, "_notify_admin", lambda payload: sent.update({"to": payload.email}))
    out = asyncio.run(sup.submit_contact(_payload(), object()))
    assert out.success is True
    assert db.inserted and db.inserted[0]["email"] == "jane@example.com"
    assert sent["to"] == "jane@example.com"


def test_submit_contact_db_failure_still_succeeds(monkeypatch):
    monkeypatch.setattr(sup.limiter, "enabled", False)

    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(sup, "get_service_supabase", _boom)
    monkeypatch.setattr(sup, "_notify_admin", lambda payload: None)
    out = asyncio.run(sup.submit_contact(_payload(), object()))
    assert out.success is True


def test_notify_admin_noop_when_email_unset(monkeypatch):
    monkeypatch.setattr(sup.settings, "support_form_email", "")
    # No raise even though Resend is not configured.
    sup._notify_admin(_payload())


def test_notify_admin_emails_via_resend(monkeypatch):
    monkeypatch.setattr(sup.settings, "support_form_email", "admin@example.com")
    monkeypatch.setattr(sup.settings, "resend_api_key", "re_x")
    fake = types.ModuleType("resend")
    captured = {}

    class Emails:
        @staticmethod
        def send(params):
            captured.update(params)

    fake.Emails = Emails
    fake.api_key = None
    monkeypatch.setitem(sys.modules, "resend", fake)
    sup._notify_admin(_payload(subject="Need help"))
    assert captured["to"] == ["admin@example.com"]
    assert captured["reply_to"] == "jane@example.com"
    assert "Need help" in captured["subject"]


def test_notify_admin_send_failure_swallowed(monkeypatch):
    monkeypatch.setattr(sup.settings, "support_form_email", "admin@example.com")
    monkeypatch.setattr(sup.settings, "resend_api_key", "re_x")
    fake = types.ModuleType("resend")

    class Emails:
        @staticmethod
        def send(params):
            raise RuntimeError("resend down")

    fake.Emails = Emails
    monkeypatch.setitem(sys.modules, "resend", fake)
    # Must not raise.
    sup._notify_admin(_payload())


def test_contact_request_rejects_bad_email():
    with pytest.raises(ValidationError):
        ContactRequest(name="x", email="not-an-email", message="hi")
