"""Tests for the Agent OS inbound-email webhook (Phase 4.2).

Covers POST /api/v1/os/inbound/email/{provider} for Postmark + Mailgun:
  - Valid signature -> 200 + bridge_email scheduled with parsed args
  - Invalid signature -> 401 + no task scheduled
  - Missing per-provider secret -> 401
  - Unknown recipient -> 404 + no task scheduled
  - Auto-reply header -> inbound_kind='auto_reply'
  - Mailgun replay window -> stale timestamp rejected
  - Missing message id -> 400

Background tasks are stubbed by conftest (_skip_background_tasks), so
the test patches BackgroundTasks.add_task to capture scheduled tasks
without executing them.
"""

import base64
import hashlib
import hmac
import json
import time

import starlette.background as starlette_background

from backend.main import app
from backend.tests.conftest import SyncASGITestClient

_CLIENT_ID = "00000000-0000-0000-0000-000000000aa1"
_RECIPIENT = "leads@tenant.agentnexlify.io"
_POSTMARK_SECRET = "test-postmark-secret"
_MAILGUN_KEY = "test-mailgun-signing-key"


# ---------------------------------------------------------------------------
# Signature helpers (mirror real provider behavior)
# ---------------------------------------------------------------------------


def _postmark_sig(body: bytes, secret: str = _POSTMARK_SECRET) -> str:
    return base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def _mailgun_sig(timestamp: str, token: str, key: str = _MAILGUN_KEY) -> str:
    return hmac.new(
        key.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------


def _make_client():
    return SyncASGITestClient(app)


def _install_capture(monkeypatch):
    """Patch BackgroundTasks.add_task to record scheduled tasks."""
    captured: list = []

    def _capture(self, func, *args, **kwargs):
        captured.append({"func": func, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(starlette_background.BackgroundTasks, "add_task", _capture)
    return captured


def _patch_tenant_resolution(monkeypatch, recipient_to_client: dict[str, str]):
    """Stub the cross-tenant inbound-address lookup."""
    from backend.services import os_inbound_bridge

    def _fake_resolve(db, recipient):
        return recipient_to_client.get(recipient)

    monkeypatch.setattr(
        os_inbound_bridge, "resolve_tenant_by_inbound_email", _fake_resolve
    )


def _patch_secrets(monkeypatch, *, postmark: str = "", mailgun: str = ""):
    from backend.config import settings

    monkeypatch.setattr(settings, "postmark_webhook_secret", postmark)
    monkeypatch.setattr(settings, "mailgun_signing_key", mailgun)


def _postmark_payload(
    *,
    message_id: str = "pm-msg-1",
    recipient: str = _RECIPIENT,
    headers: list[dict] | None = None,
) -> dict:
    return {
        "MessageID": message_id,
        "From": "customer@example.com",
        "FromName": "Test Customer",
        "OriginalRecipient": recipient,
        "Subject": "Quick question about your services",
        "TextBody": "Hi, do you have availability next week?",
        "Headers": headers or [],
    }


# ---------------------------------------------------------------------------
# Postmark
# ---------------------------------------------------------------------------


class TestPostmarkInboundEmail:
    def test_valid_signature_schedules_bridge(self, monkeypatch):
        _patch_secrets(monkeypatch, postmark=_POSTMARK_SECRET)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        payload = _postmark_payload()
        body = json.dumps(payload).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": _postmark_sig(body),
                },
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        body_json = resp.json()
        assert body_json["status"] == "accepted"
        assert body_json["inbound_kind"] == "normal"

        assert len(captured) == 1
        task_kwargs = captured[0]["kwargs"]
        assert task_kwargs["client_id"] == _CLIENT_ID
        assert task_kwargs["provider_message_id"] == "pm-msg-1"
        assert task_kwargs["inbound_kind"] == "normal"
        assert task_kwargs["sender_metadata"]["from"] == "customer@example.com"
        assert task_kwargs["sender_metadata"]["subject"].startswith("Quick question")
        assert task_kwargs["sender_metadata"]["provider"] == "postmark"

    def test_invalid_signature_returns_401(self, monkeypatch):
        _patch_secrets(monkeypatch, postmark=_POSTMARK_SECRET)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        body = json.dumps(_postmark_payload()).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": "not-the-right-signature",
                },
            )
        finally:
            client.close()

        assert resp.status_code == 401, resp.text
        assert captured == [], "bridge must not run when sig fails"

    def test_missing_secret_returns_401(self, monkeypatch):
        # Production deploy without POSTMARK_WEBHOOK_SECRET must reject,
        # not silently accept — otherwise an attacker can post anything.
        _patch_secrets(monkeypatch, postmark="")
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        body = json.dumps(_postmark_payload()).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": _postmark_sig(body, "anything"),
                },
            )
        finally:
            client.close()

        assert resp.status_code == 401, resp.text
        assert captured == []

    def test_unknown_recipient_returns_404(self, monkeypatch):
        _patch_secrets(monkeypatch, postmark=_POSTMARK_SECRET)
        _patch_tenant_resolution(monkeypatch, {})  # nobody owns this address
        captured = _install_capture(monkeypatch)

        body = json.dumps(_postmark_payload()).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": _postmark_sig(body),
                },
            )
        finally:
            client.close()

        assert resp.status_code == 404, resp.text
        assert captured == []

    def test_auto_reply_header_marks_inbound_kind(self, monkeypatch):
        _patch_secrets(monkeypatch, postmark=_POSTMARK_SECRET)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        payload = _postmark_payload(
            headers=[{"Name": "Auto-Submitted", "Value": "auto-replied"}]
        )
        body = json.dumps(payload).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": _postmark_sig(body),
                },
            )
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert resp.json()["inbound_kind"] == "auto_reply"
        assert captured[0]["kwargs"]["inbound_kind"] == "auto_reply"

    def test_missing_message_id_returns_400(self, monkeypatch):
        _patch_secrets(monkeypatch, postmark=_POSTMARK_SECRET)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        payload = _postmark_payload(message_id="")
        # Strip ALL header sources so the parser can't backfill Message-ID.
        payload["Headers"] = []
        body = json.dumps(payload).encode()

        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/postmark",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Postmark-Webhook-Hmac": _postmark_sig(body),
                },
            )
        finally:
            client.close()

        assert resp.status_code == 400, resp.text
        assert captured == []


# ---------------------------------------------------------------------------
# Mailgun
# ---------------------------------------------------------------------------


class TestMailgunInboundEmail:
    def _make_form(self, *, ts: str | None = None, token: str = "tok-1") -> dict:
        ts = ts or str(int(time.time()))
        return {
            "timestamp": ts,
            "token": token,
            "signature": _mailgun_sig(ts, token),
            "Message-Id": "mg-msg-1",
            "sender": "customer@example.com",
            "From": "Test Customer <customer@example.com>",
            "recipient": _RECIPIENT,
            "subject": "Hi from Mailgun",
            "body-plain": "Need a quote for the patio job.",
            "message-headers": json.dumps(
                [
                    ["Message-Id", "mg-msg-1"],
                    ["From", "customer@example.com"],
                ]
            ),
        }

    def test_valid_signature_schedules_bridge(self, monkeypatch):
        _patch_secrets(monkeypatch, mailgun=_MAILGUN_KEY)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = self._make_form()

        client = _make_client()
        try:
            resp = client.post("/api/v1/os/inbound/email/mailgun", data=form)
        finally:
            client.close()

        assert resp.status_code == 200, resp.text
        assert resp.json()["inbound_kind"] == "normal"
        assert len(captured) == 1
        task_kwargs = captured[0]["kwargs"]
        assert task_kwargs["client_id"] == _CLIENT_ID
        assert task_kwargs["provider_message_id"] == "mg-msg-1"
        assert task_kwargs["sender_metadata"]["provider"] == "mailgun"

    def test_invalid_signature_returns_401(self, monkeypatch):
        _patch_secrets(monkeypatch, mailgun=_MAILGUN_KEY)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = self._make_form()
        form["signature"] = "deadbeef" * 8  # wrong signature

        client = _make_client()
        try:
            resp = client.post("/api/v1/os/inbound/email/mailgun", data=form)
        finally:
            client.close()

        assert resp.status_code == 401, resp.text
        assert captured == []

    def test_stale_timestamp_rejected(self, monkeypatch):
        # Replay-window guard: > 5 minutes old must fail signature check.
        _patch_secrets(monkeypatch, mailgun=_MAILGUN_KEY)
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        stale_ts = str(int(time.time()) - 3600)  # 1 hour ago
        form = self._make_form(ts=stale_ts)

        client = _make_client()
        try:
            resp = client.post("/api/v1/os/inbound/email/mailgun", data=form)
        finally:
            client.close()

        assert resp.status_code == 401, resp.text
        assert captured == []

    def test_missing_signing_key_returns_401(self, monkeypatch):
        _patch_secrets(monkeypatch, mailgun="")
        _patch_tenant_resolution(monkeypatch, {_RECIPIENT: _CLIENT_ID})
        captured = _install_capture(monkeypatch)

        form = self._make_form()

        client = _make_client()
        try:
            resp = client.post("/api/v1/os/inbound/email/mailgun", data=form)
        finally:
            client.close()

        assert resp.status_code == 401, resp.text
        assert captured == []


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


class TestUnknownProvider:
    def test_unknown_provider_returns_422(self):
        # The Literal["postmark", "mailgun"] path param rejects other values.
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/os/inbound/email/sendgrid",
                content=b"{}",
                headers={"Content-Type": "application/json"},
            )
        finally:
            client.close()

        assert resp.status_code == 422, resp.text
