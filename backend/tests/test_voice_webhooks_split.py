"""Characterization tests for the Twilio webhooks that moved to
backend/routers/calls_webhooks.py in the calls.py split (round 7 item 3,
audit H2). Covers the three handlers the older voice suites did not
exercise end to end: call-status, recording-complete, and
transcription-complete. Behavioral contracts are unchanged by the split -
these pin them down.
"""

import os
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.background import BackgroundTasks

os.environ.setdefault("TESTING", "1")

from backend.main import app
from backend.routers import calls_webhooks
from backend.routers.automations import verify_twilio_request
from backend.tests.conftest import SyncASGITestClient

# conftest's _stable_asgi_test_execution disables BackgroundTasks.__call__ in
# tests, so handlers' queued work never executes here. These tests assert the
# ENQUEUE intent (add_task args) - the handler's contract - not execution.

_TENANT = {
    "id": "00000000-0000-0000-0000-000000000042",
    "business_name": "Split Test Plumbing",
    "notification_phone": "+15550009999",
    "plan": "agent_os",
    "voice_ai_enabled": True,
}


def _form(**fields) -> bytes:
    return urllib.parse.urlencode(fields).encode()


def _client() -> SyncASGITestClient:
    return SyncASGITestClient(app)


@pytest.fixture(autouse=True)
def _bypass_twilio_sig():
    app.dependency_overrides[verify_twilio_request] = lambda: None
    yield
    app.dependency_overrides.pop(verify_twilio_request, None)


# --- /voice/call-status -----------------------------------------------------


class TestCallStatus:
    _URL = "/api/v1/calls/voice/call-status"

    def test_completed_call_queues_finalize(self):
        finalize = MagicMock()
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=_TENANT
        ), patch.object(
            calls_webhooks, "get_service_supabase", return_value=MagicMock()
        ), patch.object(
            calls_webhooks, "_finalize_ai_call", finalize
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(
                    CallStatus="completed",
                    CallSid="CAstatus1",
                    To="+15550001111",
                    CallDuration="93",
                ),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        assert add_task.call_count == 1
        # (self, func, db, tenant_id, call_sid, duration)
        args = add_task.call_args.args
        assert args[1] is finalize
        assert args[3] == _TENANT["id"]
        assert args[4] == "CAstatus1"
        assert args[5] == 93

    def test_non_completed_status_is_ignored(self):
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=_TENANT
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(CallStatus="ringing", CallSid="CAstatus2", To="+1555"),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        add_task.assert_not_called()

    def test_unknown_tenant_returns_ok_without_finalize(self):
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=None
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(CallStatus="completed", CallSid="CAstatus3", To="+1555"),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        add_task.assert_not_called()

    def test_garbage_body_returns_ok(self):
        # Twilio retries on non-2xx; a malformed body must never 500.
        resp = _client().post(self._URL, content=b"\xff\xfe\x00garbage")
        assert resp.status_code == 200 and resp.text == "OK"

    def test_non_numeric_duration_defaults_to_zero(self):
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=_TENANT
        ), patch.object(
            calls_webhooks, "get_service_supabase", return_value=MagicMock()
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(
                    CallStatus="completed",
                    CallSid="CAstatus4",
                    To="+1555",
                    CallDuration="not-a-number",
                ),
            )
        assert resp.status_code == 200
        assert add_task.call_args.args[5] == 0


# --- /voice/recording-complete ----------------------------------------------


def _recording_db(existing_lead_rows, created_lead_rows, call_rows):
    """calls_webhooks queries leads (select/insert) then calls (insert)."""
    db = MagicMock()

    lead_select = MagicMock()
    lead_select.data = existing_lead_rows
    lead_insert = MagicMock()
    lead_insert.data = created_lead_rows
    call_insert = MagicMock()
    call_insert.data = call_rows

    def table(name):
        chain = MagicMock()
        if name == "leads":
            (
                chain.select.return_value.eq.return_value.eq.return_value
                .limit.return_value.execute.return_value
            ) = lead_select
            chain.insert.return_value.execute.return_value = lead_insert
        else:
            chain.insert.return_value.execute.return_value = call_insert
        return chain

    db.table.side_effect = table
    return db


class TestRecordingComplete:
    _URL = "/api/v1/calls/voice/recording-complete"

    def _post(self, db, send_sms, fire_event, log_activity, **overrides):
        fields = {
            "CallSid": "CArec1",
            "RecordingUrl": "https://api.twilio.com/rec/RE1",
            "RecordingDuration": "31",
            "From": "+15550002222",
            "To": "+15550001111",
            "RecordingStatus": "completed",
        }
        fields.update(overrides)
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=_TENANT
        ), patch.object(
            calls_webhooks, "get_service_supabase", return_value=db
        ), patch.object(
            calls_webhooks, "send_sms", send_sms
        ), patch.object(
            calls_webhooks, "fire_event_background", fire_event
        ), patch.object(
            calls_webhooks, "log_activity", log_activity
        ):
            return _client().post(self._URL, content=_form(**fields))

    def test_happy_path_existing_lead(self):
        db = _recording_db([{"id": "lead-1"}], [], [{"id": "call-1"}])
        send_sms = AsyncMock()
        fire_event = MagicMock()
        log_activity = MagicMock()
        resp = self._post(db, send_sms, fire_event, log_activity)
        assert resp.status_code == 200 and resp.text == "OK"
        # Owner notified about the missed call
        send_sms.assert_awaited_once()
        assert send_sms.await_args.kwargs["to"] == _TENANT["notification_phone"]
        # call.completed webhook carries the stored call + lead ids
        event = fire_event.call_args.kwargs
        assert event["event"] == "call.completed"
        assert event["data"]["call_id"] == "call-1"
        assert event["data"]["lead_id"] == "lead-1"
        assert event["data"]["duration_seconds"] == 31
        # Activity log entry tags the inbound call
        assert log_activity.call_args.kwargs["activity_type"] == "inbound_call"

    def test_new_lead_created_when_caller_unknown(self):
        db = _recording_db([], [{"id": "lead-new"}], [{"id": "call-2"}])
        fire_event = MagicMock()
        resp = self._post(db, AsyncMock(), fire_event, MagicMock())
        assert resp.status_code == 200
        assert fire_event.call_args.kwargs["data"]["lead_id"] == "lead-new"

    def test_non_completed_recording_skipped(self):
        db = _recording_db([], [], [])
        send_sms = AsyncMock()
        fire_event = MagicMock()
        resp = self._post(
            db, send_sms, fire_event, MagicMock(), RecordingStatus="in-progress"
        )
        assert resp.status_code == 200 and resp.text == "OK"
        send_sms.assert_not_awaited()
        fire_event.assert_not_called()

    def test_unknown_tenant_returns_ok(self):
        send_sms = AsyncMock()
        with patch.object(
            calls_webhooks, "_find_tenant_by_phone", return_value=None
        ), patch.object(calls_webhooks, "send_sms", send_sms):
            resp = _client().post(
                self._URL,
                content=_form(
                    CallSid="CArec3",
                    To="+15550001111",
                    From="+1555",
                    RecordingStatus="completed",
                ),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        send_sms.assert_not_awaited()

    def test_transcription_requested_when_twilio_configured(self):
        db = _recording_db([{"id": "lead-1"}], [], [{"id": "call-4"}])
        twilio_resp = MagicMock()
        twilio_resp.status_code = 201
        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=twilio_resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=http_client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch.object(
            calls_webhooks.settings, "twilio_account_sid", "ACtest"
        ), patch.object(
            calls_webhooks.settings, "twilio_auth_token", "tok"
        ), patch("httpx.AsyncClient", return_value=ctx):
            resp = self._post(
                db, AsyncMock(), MagicMock(), MagicMock(), RecordingSid="RE1"
            )
        assert resp.status_code == 200
        http_client.post.assert_awaited_once()
        assert "/Recordings/RE1/Transcriptions.json" in http_client.post.await_args.args[0]


# --- /voice/transcription-complete ------------------------------------------


def _transcription_db(call_rows):
    db = MagicMock()
    select_result = MagicMock()
    select_result.data = call_rows
    (
        db.table.return_value.select.return_value.eq.return_value
        .limit.return_value.execute.return_value
    ) = select_result
    return db


class TestTranscriptionComplete:
    _URL = "/api/v1/calls/voice/transcription-complete"

    def test_happy_path_stores_transcript_and_queues_summary(self):
        call_row = {
            "id": "call-9",
            "tenant_id": _TENANT["id"],
            "lead_id": "lead-9",
            "transcript": [{"timestamp": 0, "speaker": "assistant", "text": "Hi"}],
        }
        db = _transcription_db([call_row])
        summary = MagicMock()
        with patch.object(
            calls_webhooks, "get_service_supabase", return_value=db
        ), patch.object(
            calls_webhooks, "_generate_call_summary", summary
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(
                    TranscriptionText="I need a quote for a water heater.",
                    TranscriptionSid="TR1",
                    RecordingSid="RE1",
                    CallSid="CAtr1",
                    TranscriptionStatus="completed",
                ),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        # Transcript update merges the prior AI-conversation entries
        update_payload = db.table.return_value.update.call_args.args[0]
        texts = [e["text"] for e in update_payload["transcript"]]
        assert texts == ["Hi", "I need a quote for a water heater."]
        # Summary generation queued with the merged transcript text
        assert add_task.call_args.args[1] is summary
        kwargs = add_task.call_args.kwargs
        assert kwargs["call_id"] == "call-9"
        assert kwargs["tenant_id"] == _TENANT["id"]
        assert "[assistant]: Hi" in kwargs["transcript_text"]
        assert "water heater" in kwargs["transcript_text"]

    def test_unknown_call_sid_returns_ok_without_summary(self):
        db = _transcription_db([])
        with patch.object(
            calls_webhooks, "get_service_supabase", return_value=db
        ), patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(
                    TranscriptionText="hello", CallSid="CAmissing",
                ),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        add_task.assert_not_called()

    def test_failed_transcription_status_skipped(self):
        with patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            resp = _client().post(
                self._URL,
                content=_form(
                    TranscriptionText="text",
                    CallSid="CAtr2",
                    TranscriptionStatus="failed",
                ),
            )
        assert resp.status_code == 200 and resp.text == "OK"
        add_task.assert_not_called()

    def test_empty_text_and_missing_sid_are_noops(self):
        with patch.object(BackgroundTasks, "add_task", autospec=True) as add_task:
            empty = _client().post(
                self._URL,
                content=_form(TranscriptionText="   ", CallSid="CAtr3"),
            )
            no_sid = _client().post(
                self._URL, content=_form(TranscriptionText="real text")
            )
        assert empty.status_code == 200 and empty.text == "OK"
        assert no_sid.status_code == 200 and no_sid.text == "OK"
        add_task.assert_not_called()


# --- voice_phone_routing lead helper ----------------------------------------


class TestFindOrCreateLead:
    def test_creates_lead_when_none_exists(self):
        from backend.services.voice_phone_routing import _find_or_create_lead

        db = _recording_db([], [{"id": "lead-created"}], [])
        assert (
            _find_or_create_lead(db, _TENANT["id"], "+1555", "Inbound phone call")
            == "lead-created"
        )

    def test_returns_existing_lead(self):
        from backend.services.voice_phone_routing import _find_or_create_lead

        db = _recording_db([{"id": "lead-existing"}], [], [])
        assert (
            _find_or_create_lead(db, _TENANT["id"], "+1555", "note")
            == "lead-existing"
        )

    def test_db_error_returns_none(self):
        from backend.services.voice_phone_routing import _find_or_create_lead

        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert _find_or_create_lead(db, _TENANT["id"], "+1555", "note") is None
