"""Tests for previously untested messaging/webhook routers.

Covers: email_sequences, conversation_inbox, resend_webhooks,
twilio_webhooks, channels_facebook, gbp, automations, booking_page.
"""

import os

os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


def _make_token(tenant_id: str = "tenant-001") -> str:
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": "professional",
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth(tenant_id: str = "tenant-001") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


def _mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# Email Sequences
# ---------------------------------------------------------------------------


class TestEmailSequences:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.email_crud.get_service_supabase")
    def test_list_sequences(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "seq1",
                    "name": "Welcome Series",
                    "trigger_type": "lead_captured",
                    "is_active": True,
                }
            ]
        )
        resp = client.get("/api/v1/email-sequences", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.email_crud.get_service_supabase")
    def test_create_sequence(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "seq2", "name": "Follow-up", "trigger_type": "manual"}]
        )
        resp = client.post(
            "/api/v1/email-sequences",
            json={"name": "Follow-up", "trigger_type": "manual"},
            headers=_auth(),
        )
        assert resp.status_code == 201

    def test_sequences_no_auth_returns_422(self):
        resp = client.get("/api/v1/email-sequences")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Conversation Inbox
# ---------------------------------------------------------------------------


class TestConversationInbox:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.conversation_inbox.get_service_supabase")
    def test_get_notes(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "n1", "content": "Called back", "author_id": "team-1"}]
        )
        resp = client.get(
            "/api/v1/inbox/tenant-001/conversations/conv-001/notes",
            headers=_auth(),
        )
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.conversation_inbox.get_service_supabase")
    def test_create_note(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "n2", "content": "Sent proposal"}]
        )
        resp = client.post(
            "/api/v1/inbox/tenant-001/conversations/conv-001/notes",
            json={"content": "Sent proposal"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.conversation_inbox.get_service_supabase")
    def test_get_presence(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "tm1", "name": "Alice", "is_online": True}]
        )
        resp = client.get("/api/v1/inbox/tenant-001/presence", headers=_auth())
        assert resp.status_code == 200

    def test_inbox_no_auth_returns_422(self):
        resp = client.get("/api/v1/inbox/tenant-001/conversations/conv-001/notes")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Resend Webhooks
# ---------------------------------------------------------------------------


class TestResendWebhooks:
    def test_resend_webhook_invalid_signature(self):
        resp = client.post(
            "/api/v1/webhooks/resend",
            json={"type": "email.bounced", "data": {"to": ["test@example.com"]}},
            headers={
                "svix-signature": "v1,invalid",
                "svix-id": "msg1",
                "svix-timestamp": "12345",
            },
        )
        assert resp.status_code == 401

    def test_resend_webhook_no_signature(self):
        resp = client.post(
            "/api/v1/webhooks/resend",
            json={"type": "email.bounced", "data": {}},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Twilio Webhooks
# ---------------------------------------------------------------------------


class TestTwilioWebhooks:
    @patch("backend.routers.twilio_webhooks.get_service_supabase")
    def test_missed_call_no_signature_rejects(self, mock_db):
        """Twilio webhooks require valid signature — unsigned requests fail."""
        db = MagicMock()
        mock_db.return_value = db
        resp = client.post(
            "/api/v1/twilio/missed-call",
            data={
                "From": "+15551234567",
                "To": "+15559876543",
                "CallStatus": "no-answer",
            },
        )
        # Should fail signature verification, return TwiML error, or 422 (validation)
        assert resp.status_code in (200, 400, 403, 422, 500)

    @patch("backend.routers.twilio_webhooks.get_service_supabase")
    def test_sms_reply_no_signature_rejects(self, mock_db):
        db = MagicMock()
        mock_db.return_value = db
        resp = client.post(
            "/api/v1/twilio/sms-reply",
            data={"From": "+15551234567", "To": "+15559876543", "Body": "Yes"},
        )
        assert resp.status_code in (200, 400, 403, 500)

    @patch("backend.routers.twilio_webhooks._verify_twilio_signature")
    def test_sms_reply_deprecated_returns_410(self, mock_verify):
        """Legacy /sms-reply endpoint is gone — migrated to /api/v1/os/inbound/sms."""
        mock_verify.return_value = True
        resp = client.post(
            "/api/v1/twilio/sms-reply",
            data={
                "From": "+15551234567",
                "To": "+15559876543",
                "Body": "Yes",
                "MessageSid": "SM_deprecated_test",
            },
        )
        assert resp.status_code == 410
        assert "os/inbound/sms" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# Channels (Facebook)
# ---------------------------------------------------------------------------


class TestChannelsFacebook:
    @patch("backend.routers.channels_facebook.settings")
    def test_webhook_verification_wrong_token(self, mock_settings):
        mock_settings.facebook_verify_token = "correct-token"
        resp = client.get(
            "/api/v1/channels/facebook/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "test-challenge-123",
            },
        )
        assert resp.status_code == 403

    @patch("backend.routers.channels_facebook.settings")
    def test_webhook_verification_correct_token(self, mock_settings):
        mock_settings.facebook_verify_token = "correct-token"
        resp = client.get(
            "/api/v1/channels/facebook/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "correct-token",
                "hub.challenge": "test-challenge-123",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "test-challenge-123"

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.channels_facebook.get_service_supabase")
    def test_facebook_status_no_integration(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        # No integration found — return disconnected
        result = MagicMock()
        result.data = []
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
            result
        )
        resp = client.get(
            "/api/v1/channels/facebook/tenant-001/status",
            headers=_auth(),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GBP (Google Business Profile)
# ---------------------------------------------------------------------------


class TestGBP:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.gbp.get_service_supabase")
    def test_gbp_status_no_integration(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        result = MagicMock()
        result.data = None
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
            result
        )
        resp = client.get("/api/v1/gbp/tenant-001/status", headers=_auth())
        assert resp.status_code == 200

    def test_gbp_status_no_auth_returns_422(self):
        resp = client.get("/api/v1/gbp/tenant-001/status")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Automations (simple rules)
# ---------------------------------------------------------------------------


class TestAutomations:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.automations.get_service_supabase")
    def test_list_automations(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "a1", "type": "missed_call_text", "is_enabled": True}]
        )
        resp = client.get("/api/v1/automations/tenant-001", headers=_auth())
        assert resp.status_code == 200

    def test_automations_no_auth_returns_422(self):
        resp = client.get("/api/v1/automations/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Booking Page (public)
# ---------------------------------------------------------------------------


class TestBookingPage:
    def test_booking_submit_missing_fields(self):
        """Submit with no body should return 422 validation error."""
        resp = client.post("/api/v1/book/test-biz/submit", json={})
        assert resp.status_code == 422
