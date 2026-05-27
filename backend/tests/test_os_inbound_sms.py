"""Tests for the Agent OS inbound-SMS webhook (Phase 5.1).

Covers POST /api/v1/os/inbound/sms (Twilio):
  - Valid signature -> 200 TwiML + bridge_sms scheduled
  - Invalid signature -> 403 + no task scheduled
  - Missing TWILIO_AUTH_TOKEN -> 403 (refuse silently-unverifiable webhook)
  - STOP keyword -> leads.unsubscribed flipped + system_notice inbound_kind
  - Unknown To number -> 404 + no task scheduled

Background tasks are stubbed via `BackgroundTasks.add_task` patch, so
the test captures scheduled work without executing it. Twilio signature
matches ``inbound_sms_verify.verify_twilio`` exactly — HMAC-SHA1 of
URL + sorted form params concatenated, base64-encoded.
"""

import base64
import hashlib
import hmac
from urllib.parse import urlencode

import starlette.background as starlette_background

from backend.main import app
from backend.tests.conftest import SyncASGITestClient

_CLIENT_ID = "00000000-0000-0000-0000-000000000bb1"
_TWILIO_TOKEN = "test-twilio-auth-token"
_TENANT_TO = "+15551234567"
_CUSTOMER_FROM = "+15559876543"
_WEBHOOK_URL = "http://testserver/api/v1/os/inbound/sms"


def _twilio_sig(url: str, form: dict[str, str], token: str = _TWILIO_TOKEN) -> str:
    payload = url + "".join(f"{k}{form[k]}" for k in sorted(form))
    digest = hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _make_client():
    return SyncASGITestClient(app)


def _install_capture(monkeypatch):
    """Patch BackgroundTasks.add_task to record scheduled tasks."""
    captured: list = []

    def _capture(self, func, *args, **kwargs):
        captured.append({"func": func, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(starlette_background.BackgroundTasks, "add_task", _capture)
    return captured


def _patch_phone_resolution(monkeypatch, mapping: dict[str, str]):
    """Stub the cross-tenant phone -> client lookup."""
    from backend.services import os_inbound_bridge

    def _fake_resolve(db, to_number):
        return mapping.get(to_number)

    monkeypatch.setattr(
        os_inbound_bridge, "resolve_tenant_by_inbound_phone", _fake_resolve
    )


def _patch_token(monkeypatch, token: str = _TWILIO_TOKEN):
    from backend.config import settings

    monkeypatch.setattr(settings, "twilio_auth_token", token)


def _form_payload(
    *,
    to: str = _TENANT_TO,
    from_: str = _CUSTOMER_FROM,
    body: str = "Hi, are you open Saturday?",
    sid: str = "SM-test-1",
) -> dict[str, str]:
    return {
        "To": to,
        "From": from_,
        "Body": body,
        "MessageSid": sid,
        "AccountSid": "AC-test",
        "NumMedia": "0",
    }


class TestTwilioInboundSMS:
    def test_valid_signature_schedules_bridge(self, monkeypatch):
        _patch_token(monkeypatch)
        _patch_phone_resolution(monkeypatch, {_TENANT_TO: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = _form_payload()
        sig = _twilio_sig(_WEBHOOK_URL, form)

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/sms",
                content=urlencode(form).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": sig,
                },
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/xml")
        assert "<Response/>" in resp.text

        assert len(captured) == 1
        task_kwargs = captured[0]["kwargs"]
        assert task_kwargs["client_id"] == _CLIENT_ID
        assert task_kwargs["provider_message_id"] == "SM-test-1"
        assert task_kwargs["inbound_kind"] == "normal"
        assert task_kwargs["user_content"] == "Hi, are you open Saturday?"
        assert task_kwargs["sender_metadata"]["from"] == _CUSTOMER_FROM
        assert task_kwargs["sender_metadata"]["to"] == _TENANT_TO
        assert task_kwargs["sender_metadata"]["provider"] == "twilio"
        assert task_kwargs["sender_metadata"]["stop_keyword"] is False

    def test_invalid_signature_returns_403(self, monkeypatch):
        _patch_token(monkeypatch)
        _patch_phone_resolution(monkeypatch, {_TENANT_TO: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = _form_payload()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/sms",
                content=urlencode(form).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": "not-the-right-signature",
                },
            )
        finally:
            client.close()

        assert resp.status_code == 403, resp.text
        assert captured == [], "bridge must not run when sig fails"

    def test_missing_auth_token_returns_403(self, monkeypatch):
        # Production deploy without TWILIO_AUTH_TOKEN must reject —
        # otherwise an attacker can post anything.
        _patch_token(monkeypatch, token="")
        _patch_phone_resolution(monkeypatch, {_TENANT_TO: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = _form_payload()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/sms",
                content=urlencode(form).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": "anything",
                },
            )
        finally:
            client.close()

        assert resp.status_code == 403, resp.text
        assert captured == []

    def test_unknown_to_number_returns_404(self, monkeypatch):
        _patch_token(monkeypatch)
        _patch_phone_resolution(monkeypatch, {})  # nobody owns this number
        captured = _install_capture(monkeypatch)

        form = _form_payload()
        sig = _twilio_sig(_WEBHOOK_URL, form)

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/sms",
                content=urlencode(form).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": sig,
                },
            )
        finally:
            client.close()

        assert resp.status_code == 404, resp.text
        assert captured == []

    def test_stop_keyword_flips_unsubscribed_and_marks_system_notice(
        self, monkeypatch, mock_supabase
    ):
        _patch_token(monkeypatch)
        _patch_phone_resolution(monkeypatch, {_TENANT_TO: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        # Stub the leads-select chain so _flip_lead_unsubscribed finds a match.
        lead_id = "00000000-0000-0000-0000-0000000000cc1"
        update_calls: list = []

        class _FakeQuery:
            def __init__(self, *, table_name: str):
                self._table = table_name

            def select(self, *_a, **_kw):
                return self

            def eq(self, *_a, **_kw):
                return self

            def not_(self):
                return self

            def is_(self, *_a, **_kw):
                return self

            def filter(self, *_a, **_kw):
                return self

            def in_(self, col, ids):
                update_calls.append({"op": "in_", "col": col, "ids": ids})
                return self

            def update(self, payload):
                update_calls.append({"op": "update", "payload": payload})
                return self

            def execute(self):
                if (
                    self._table == "leads"
                    and update_calls
                    and update_calls[-1].get("op") == "update"
                ):
                    return type("R", (), {"data": []})()
                # leads-select returns one matching row by phone last-10
                return type(
                    "R", (), {"data": [{"id": lead_id, "phone": _CUSTOMER_FROM}]}
                )()

        # leads.select returns the fake query above; in_/update chain
        # captures the UPDATE for assertion.
        class _Chain:
            def __init__(self, name):
                self.name = name
                self._q = _FakeQuery(table_name=name)

            def __getattr__(self, attr):
                return getattr(self._q, attr)

        mock_supabase.table.side_effect = lambda name: _Chain(name)
        # `_Chain.not_` is a method, but the route does `.not_.is_(...)` —
        # chain `not_` returns the same query object so `.is_` is callable.

        form = _form_payload(body="STOP")
        sig = _twilio_sig(_WEBHOOK_URL, form)

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/sms",
                content=urlencode(form).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": sig,
                },
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert len(captured) == 1
        task_kwargs = captured[0]["kwargs"]
        assert task_kwargs["inbound_kind"] == "system_notice"
        assert task_kwargs["sender_metadata"]["stop_keyword"] is True

        # Verify the UPDATE was issued with unsubscribed=true for matched id.
        update_ops = [c for c in update_calls if c["op"] == "update"]
        in_ops = [c for c in update_calls if c["op"] == "in_"]
        assert update_ops, "expected leads UPDATE on STOP keyword"
        assert update_ops[0]["payload"]["unsubscribed"] is True
        assert "unsubscribed_at" in update_ops[0]["payload"]
        assert in_ops and lead_id in in_ops[0]["ids"]
