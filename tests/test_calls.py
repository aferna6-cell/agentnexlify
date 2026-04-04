"""Tests for the AI Answering Service (calls) endpoints."""

import os
os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch, AsyncMock
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import MockSupabaseClient, MockSupabaseResponse, MockSupabaseTable


client = TestClient(app)

# The JWT secret used for test tokens must match what _decode_token reads.
_TEST_SECRET = "test-secret-key-for-jwt"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(tenant_id: str = "tenant-001") -> str:
    """Create a valid JWT for testing."""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": "growth",
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth_header(tenant_id: str = "tenant-001") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name.

    table_responses: dict of {table_name: (data_list, count)}
    Supports chained calls: .select().eq().limit().order().range().execute()
    """
    def mock_table(name):
        data, count = table_responses.get(name, ([], None))

        table = MagicMock()
        for method in [
            "select", "insert", "update", "delete",
            "eq", "neq", "gte", "lte", "gt", "lt",
            "limit", "order", "ilike", "range",
            "in_", "is_", "or_", "contains",
        ]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = data
        result.count = count if count is not None else len(data)
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


# ---------------------------------------------------------------------------
# Voice incoming tests
# ---------------------------------------------------------------------------


class TestVoiceIncoming:
    """Tests for POST /api/v1/calls/voice/incoming."""

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_incoming_call_returns_twiml(self, mock_find):
        mock_find.return_value = {
            "id": "tenant-001",
            "business_name": "Acme Plumbing",
            "owner_email": "owner@acme.com",
            "notification_phone": "+15551234567",
        }

        form_data = urlencode({
            "From": "+15559998888",
            "To": "+15551234567",
            "CallSid": "CA123abc",
            "CallStatus": "ringing",
        })

        resp = client.post(
            "/api/v1/calls/voice/incoming",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        body = resp.text
        assert "<Response>" in body
        assert "Acme Plumbing" in body
        # Incoming calls now use Gather for AI conversation instead of Record
        assert "<Gather" in body
        assert 'input="speech"' in body
        assert "voice/respond" in body

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_incoming_call_no_tenant(self, mock_find):
        mock_find.return_value = None

        form_data = urlencode({
            "From": "+15559998888",
            "To": "+15550000000",
            "CallSid": "CA456def",
        })

        resp = client.post(
            "/api/v1/calls/voice/incoming",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert "<Response>" in resp.text
        assert "unable to take your call" in resp.text

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_incoming_call_empty_body(self, mock_find):
        mock_find.return_value = None

        resp = client.post(
            "/api/v1/calls/voice/incoming",
            content="",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # Should still return valid TwiML (error response)
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_incoming_call_xml_escapes_business_name(self, mock_find):
        mock_find.return_value = {
            "id": "tenant-001",
            "business_name": "Bob's <Plumbing> & Co",
            "owner_email": "bob@test.com",
            "notification_phone": "+15551234567",
        }

        form_data = urlencode({
            "From": "+15559998888",
            "To": "+15551234567",
            "CallSid": "CA789ghi",
        })

        resp = client.post(
            "/api/v1/calls/voice/incoming",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        body = resp.text
        # Should be XML-escaped, not raw angle brackets
        assert "&lt;Plumbing&gt;" in body
        assert "&amp; Co" in body
        assert "Bob&apos;s" in body


# ---------------------------------------------------------------------------
# Recording complete tests
# ---------------------------------------------------------------------------


class TestRecordingComplete:
    """Tests for POST /api/v1/calls/voice/recording-complete."""

    @patch("backend.routers.calls.fire_event_background")
    @patch("backend.routers.calls.send_sms", new_callable=AsyncMock)
    @patch("backend.routers.calls.log_activity")
    @patch("backend.routers.calls._find_tenant_by_phone")
    @patch("backend.routers.calls.get_supabase")
    def test_recording_complete_stores_call(
        self, mock_db, mock_find, mock_activity, mock_sms, mock_fire
    ):
        mock_find.return_value = {
            "id": "tenant-001",
            "business_name": "Acme Plumbing",
            "owner_email": "owner@acme.com",
            "notification_phone": "+15551234567",
        }

        # Mock DB client
        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "leads": ([{"id": "lead-uuid-001"}], 1),
            "calls": ([{"id": "call-uuid-001"}], 1),
        })

        form_data = urlencode({
            "CallSid": "CA123abc",
            "RecordingUrl": "https://api.twilio.com/recordings/RE123",
            "RecordingDuration": "45",
            "RecordingStatus": "completed",
            "From": "+15559998888",
            "To": "+15551234567",
        })

        resp = client.post(
            "/api/v1/calls/voice/recording-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.text == "OK"

        # Verify activity was logged
        mock_activity.assert_called_once()
        call_args = mock_activity.call_args
        assert call_args.kwargs["tenant_id"] == "tenant-001"
        assert call_args.kwargs["activity_type"] == "inbound_call"

        # Verify SMS notification was sent
        mock_sms.assert_called_once()

        # Verify webhook was fired
        mock_fire.assert_called_once()
        fire_args = mock_fire.call_args
        assert fire_args[1]["event"] == "call.completed" or fire_args[0][1] == "call.completed"

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_recording_skipped_if_not_completed(self, mock_find):
        """Non-completed recording statuses should be skipped."""
        mock_find.return_value = {
            "id": "tenant-001",
            "business_name": "Test",
        }

        form_data = urlencode({
            "CallSid": "CA123abc",
            "RecordingUrl": "https://api.twilio.com/recordings/RE123",
            "RecordingDuration": "0",
            "RecordingStatus": "failed",
            "From": "+15559998888",
            "To": "+15551234567",
        })

        resp = client.post(
            "/api/v1/calls/voice/recording-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.text == "OK"

    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_recording_no_tenant(self, mock_find):
        mock_find.return_value = None

        form_data = urlencode({
            "CallSid": "CA123abc",
            "RecordingUrl": "https://api.twilio.com/recordings/RE123",
            "RecordingDuration": "30",
            "RecordingStatus": "completed",
            "From": "+15559998888",
            "To": "+15550000000",
        })

        resp = client.post(
            "/api/v1/calls/voice/recording-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard endpoint tests — patch auth settings where it's imported
# ---------------------------------------------------------------------------


class TestListCalls:
    """Tests for GET /api/v1/calls/{tenant_id}."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.calls.get_supabase")
    def test_list_calls_success(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": (
                [
                    {
                        "id": "call-001",
                        "tenant_id": "tenant-001",
                        "caller_phone": "+15559998888",
                        "called_number": "+15551234567",
                        "direction": "inbound",
                        "duration_seconds": 30,
                        "status": "completed",
                        "recording_url": "https://example.com/rec",
                        "transcript": [],
                        "summary": "Test call",
                        "sentiment": None,
                        "action_taken": None,
                        "twilio_call_sid": "CA123",
                        "created_at": "2026-03-15T10:00:00Z",
                        "lead_id": None,
                    },
                ],
                1,
            ),
        })

        resp = client.get(
            "/api/v1/calls/tenant-001",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["calls"]) == 1
        assert data["calls"][0]["caller_phone"] == "+15559998888"

    @patch("backend.routers.auth.settings")
    def test_list_calls_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/calls/tenant-002",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


class TestGetCallStats:
    """Tests for GET /api/v1/calls/{tenant_id}/stats."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.calls.get_supabase")
    def test_stats_returns_defaults(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": ([], 0),
        })

        resp = client.get(
            "/api/v1/calls/tenant-001/stats",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 0
        assert data["missed_calls"] == 0
        assert data["avg_duration_seconds"] == 0.0
        assert data["calls_today"] == 0

    @patch("backend.routers.auth.settings")
    def test_stats_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/calls/tenant-002/stats",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


class TestGetCall:
    """Tests for GET /api/v1/calls/{tenant_id}/{call_id}."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.calls.get_supabase")
    def test_get_call_success(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": (
                [
                    {
                        "id": "call-001",
                        "tenant_id": "tenant-001",
                        "caller_phone": "+15559998888",
                        "called_number": "+15551234567",
                        "direction": "inbound",
                        "duration_seconds": 45,
                        "status": "completed",
                        "recording_url": "https://example.com/rec",
                        "transcript": [],
                        "summary": "Caller asked about pricing",
                        "sentiment": "positive",
                        "action_taken": None,
                        "twilio_call_sid": "CA123",
                        "created_at": "2026-03-15T10:00:00Z",
                        "lead_id": "lead-001",
                    },
                ],
                1,
            ),
        })

        resp = client.get(
            "/api/v1/calls/tenant-001/call-001",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "call-001"
        assert data["summary"] == "Caller asked about pricing"

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.calls.get_supabase")
    def test_get_call_not_found(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": ([], 0),
        })

        resp = client.get(
            "/api/v1/calls/tenant-001/nonexistent-call",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 404

    @patch("backend.routers.auth.settings")
    def test_get_call_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/calls/tenant-002/call-001",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TwiML helper tests
# ---------------------------------------------------------------------------


class TestTwimlHelpers:
    """Unit tests for TwiML generation helpers."""

    def test_build_twiml_greeting(self):
        from backend.routers.calls import _build_twiml_greeting

        twiml = _build_twiml_greeting("Test Business", "https://example.com/callback")
        assert '<?xml version="1.0"' in twiml
        assert "<Response>" in twiml
        assert "Test Business" in twiml
        assert "<Record" in twiml
        assert 'maxLength="120"' in twiml
        assert "https://example.com/callback" in twiml

    def test_build_twiml_greeting_with_transcription(self):
        from backend.routers.calls import _build_twiml_greeting

        twiml = _build_twiml_greeting(
            "Test Business",
            "https://example.com/callback",
            transcription_callback_url="https://example.com/transcription",
        )
        assert 'transcribe="true"' in twiml
        assert 'transcriptionUrl="https://example.com/transcription"' in twiml

    def test_build_twiml_greeting_without_transcription(self):
        from backend.routers.calls import _build_twiml_greeting

        twiml = _build_twiml_greeting("Test Business", "https://example.com/callback")
        assert "transcribe" not in twiml
        assert "transcriptionUrl" not in twiml

    def test_build_twiml_error(self):
        from backend.routers.calls import _build_twiml_error

        twiml = _build_twiml_error()
        assert "<Response>" in twiml
        assert "unable to take your call" in twiml

    def test_twiml_greeting_escapes_special_chars(self):
        from backend.routers.calls import _build_twiml_greeting

        twiml = _build_twiml_greeting(
            "Bob's <Fish> & Chips",
            "https://example.com/cb",
        )
        assert "&lt;Fish&gt;" in twiml
        assert "&amp; Chips" in twiml
        assert "Bob&apos;s" in twiml


# ---------------------------------------------------------------------------
# Transcription complete tests
# ---------------------------------------------------------------------------


class TestTranscriptionComplete:
    """Tests for POST /api/v1/calls/voice/transcription-complete."""

    @patch("backend.routers.calls.get_supabase")
    def test_transcription_stores_and_triggers_summary(self, mock_db):
        """Completed transcription should store transcript and trigger background summary."""
        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": (
                [
                    {
                        "id": "call-uuid-001",
                        "tenant_id": "tenant-001",
                        "lead_id": "lead-uuid-001",
                        "transcript": [],
                    }
                ],
                1,
            ),
        })

        form_data = urlencode({
            "TranscriptionText": "Hi, I need a plumber for my kitchen sink.",
            "TranscriptionSid": "TR123abc",
            "RecordingSid": "RE123abc",
            "CallSid": "CA123abc",
            "TranscriptionStatus": "completed",
        })

        resp = client.post(
            "/api/v1/calls/voice/transcription-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_transcription_empty_text(self):
        """Empty transcription text should be handled gracefully."""
        form_data = urlencode({
            "TranscriptionText": "",
            "TranscriptionSid": "TR123abc",
            "RecordingSid": "RE123abc",
            "CallSid": "CA123abc",
            "TranscriptionStatus": "completed",
        })

        resp = client.post(
            "/api/v1/calls/voice/transcription-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_transcription_missing_call_sid(self):
        """Missing CallSid should be handled gracefully."""
        form_data = urlencode({
            "TranscriptionText": "Hello world",
            "TranscriptionSid": "TR123abc",
            "RecordingSid": "RE123abc",
            "TranscriptionStatus": "completed",
        })

        resp = client.post(
            "/api/v1/calls/voice/transcription-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200

    @patch("backend.routers.calls.get_supabase")
    def test_transcription_unknown_call_sid(self, mock_db):
        """Transcription for an unknown call SID should return OK without error."""
        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": ([], 0),
        })

        form_data = urlencode({
            "TranscriptionText": "Test transcription text",
            "TranscriptionSid": "TR123abc",
            "RecordingSid": "RE123abc",
            "CallSid": "CA_UNKNOWN",
            "TranscriptionStatus": "completed",
        })

        resp = client.post(
            "/api/v1/calls/voice/transcription-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200

    def test_transcription_failed_status_skipped(self):
        """Non-completed transcription status should be skipped."""
        form_data = urlencode({
            "TranscriptionText": "Some text",
            "TranscriptionSid": "TR123abc",
            "RecordingSid": "RE123abc",
            "CallSid": "CA123abc",
            "TranscriptionStatus": "failed",
        })

        resp = client.post(
            "/api/v1/calls/voice/transcription-complete",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.text == "OK"


# ---------------------------------------------------------------------------
# Voice respond tests
# ---------------------------------------------------------------------------


class TestVoiceRespond:
    """Tests for POST /api/v1/calls/voice/respond."""

    @patch("backend.routers.calls.call_claude_messages", new_callable=AsyncMock)
    @patch("backend.routers.calls.get_supabase")
    @patch("backend.routers.calls._find_tenant_by_phone")
    def test_voice_respond_uses_llm_runtime(self, mock_find, mock_db, mock_call_claude):
        mock_find.return_value = {
            "id": "tenant-001",
            "business_name": "Acme Plumbing",
        }

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "chat_messages": (
                [{"role": "assistant", "content": "Thanks for calling Acme Plumbing!"}],
                1,
            ),
            "tenants": (
                [{
                    "business_name": "Acme Plumbing",
                    "business_type": "plumbing",
                    "owner_email": "owner@acme.com",
                }],
                1,
            ),
            "faq_entries": (
                [{"question": "Do you offer emergency service?", "answer": "Yes, 24/7."}],
                1,
            ),
        })

        mock_call_claude.return_value = MagicMock(
            text="We can help with that. What address should we send the technician to?",
            duration_ms=140,
        )

        form_data = urlencode({
            "SpeechResult": "I need help with a leaking water heater.",
            "CallSid": "CA-voice-001",
            "From": "+15559998888",
            "To": "+15551234567",
        })

        resp = client.post(
            "/api/v1/calls/voice/respond?round=1",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "What address should we send the technician to?" in resp.text
        mock_call_claude.assert_awaited_once()


# ---------------------------------------------------------------------------
# AI summary generation unit tests
# ---------------------------------------------------------------------------


class TestGenerateCallSummary:
    """Unit tests for _generate_call_summary."""

    @pytest.mark.asyncio
    @patch("backend.routers.calls.log_activity")
    @patch("backend.routers.calls.get_supabase")
    @patch("backend.routers.calls.call_claude_messages", new_callable=AsyncMock)
    async def test_summary_parses_json_response(self, mock_call_claude, mock_db, mock_activity):
        """Summary should parse Claude's JSON response and update the call."""
        from backend.routers.calls import _generate_call_summary

        mock_call_claude.return_value = MagicMock(
            text='{"summary": "Caller asked about pricing.", "action_items": ["Send quote by Friday"], "sentiment": "positive", "follow_up": "Email pricing sheet"}',
            duration_ms=175,
        )

        # Mock DB
        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "calls": ([{"id": "call-001"}], 1),
            "action_items": ([{"id": "ai-001"}], 1),
        })

        await _generate_call_summary(
            call_id="call-001",
            tenant_id="tenant-001",
            lead_id="lead-001",
            transcript_text="Caller: How much for a kitchen remodel?",
        )

        mock_call_claude.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_summary_skips_empty_transcript(self):
        """Empty transcript should skip summary generation."""
        from backend.routers.calls import _generate_call_summary

        # Should return without error
        await _generate_call_summary(
            call_id="call-001",
            tenant_id="tenant-001",
            lead_id=None,
            transcript_text="",
        )

    @pytest.mark.asyncio
    async def test_summary_skips_whitespace_transcript(self):
        """Whitespace-only transcript should skip summary generation."""
        from backend.routers.calls import _generate_call_summary

        await _generate_call_summary(
            call_id="call-001",
            tenant_id="tenant-001",
            lead_id=None,
            transcript_text="   \n  ",
        )


# ---------------------------------------------------------------------------
# Action item insertion unit tests
# ---------------------------------------------------------------------------


class TestInsertCallActionItems:
    """Unit tests for _insert_call_action_items."""

    @pytest.mark.asyncio
    @patch("backend.routers.calls.log_activity")
    @patch("backend.routers.calls.get_supabase")
    async def test_inserts_action_items(self, mock_db, mock_activity):
        """Should insert each action item into action_items table."""
        from backend.routers.calls import _insert_call_action_items

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "action_items": ([{"id": "ai-001"}], 1),
        })

        await _insert_call_action_items(
            tenant_id="tenant-001",
            lead_id="lead-001",
            call_id="call-001",
            items=["Send quote by Friday", "Schedule follow-up call"],
        )

        # Verify activity was logged
        mock_activity.assert_called_once()
        call_args = mock_activity.call_args
        assert call_args.kwargs["activity_type"] == "call_action_items"
        assert call_args.kwargs["tenant_id"] == "tenant-001"

    @pytest.mark.asyncio
    @patch("backend.routers.calls.log_activity")
    @patch("backend.routers.calls.get_supabase")
    async def test_skips_empty_items(self, mock_db, mock_activity):
        """Empty item list should not insert anything."""
        from backend.routers.calls import _insert_call_action_items

        await _insert_call_action_items(
            tenant_id="tenant-001",
            lead_id=None,
            call_id="call-001",
            items=[],
        )

        # Should not call DB or log activity
        mock_db.assert_not_called()
        mock_activity.assert_not_called()

    @pytest.mark.asyncio
    @patch("backend.routers.calls.log_activity")
    @patch("backend.routers.calls.get_supabase")
    async def test_sets_high_priority(self, mock_db, mock_activity):
        """Call action items should always be high priority."""
        from backend.routers.calls import _insert_call_action_items

        mock_client = MagicMock()
        mock_db.return_value = mock_client

        # Track what gets inserted
        insert_calls = []
        table_mock = MagicMock()
        for method in ["select", "insert", "update", "delete", "eq", "limit", "order"]:
            getattr(table_mock, method).return_value = table_mock
        result = MagicMock()
        result.data = [{"id": "ai-001"}]
        table_mock.execute.return_value = result

        def track_insert(data):
            insert_calls.append(data)
            return table_mock

        table_mock.insert = track_insert
        mock_client.table.return_value = table_mock

        await _insert_call_action_items(
            tenant_id="tenant-001",
            lead_id="lead-001",
            call_id="call-001",
            items=["Follow up with client"],
        )

        assert len(insert_calls) == 1
        assert insert_calls[0]["priority"] == "high"
        assert insert_calls[0]["status"] == "pending"
        assert insert_calls[0]["tenant_id"] == "tenant-001"
        assert insert_calls[0]["lead_id"] == "lead-001"


# ---------------------------------------------------------------------------
# Webhook event registration test
# ---------------------------------------------------------------------------


class TestWebhookEventRegistered:
    """Verify call.completed is in SUPPORTED_EVENTS."""

    def test_call_completed_event_supported(self):
        from backend.services.webhook_dispatcher import SUPPORTED_EVENTS

        assert "call.completed" in SUPPORTED_EVENTS
