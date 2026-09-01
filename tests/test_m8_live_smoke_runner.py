"""Unit tests for M8 live smoke runner helpers (no staging I/O)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("m8_live_smoke", SCRIPTS / "m8_live_smoke.py")
m8 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m8)


class TestGmailRecipientGate:
    def test_requires_recipient(self, monkeypatch):
        monkeypatch.delenv("M8_SMOKE_GMAIL_RECIPIENT", raising=False)
        recipient, blocker = m8._gmail_recipient_allowed()
        assert recipient is None
        assert "M8_SMOKE_GMAIL_RECIPIENT" in (blocker or "")

    def test_allowlist_enforced(self, monkeypatch):
        monkeypatch.setenv("M8_SMOKE_GMAIL_RECIPIENT", "smoke@example.com")
        monkeypatch.setenv(
            "M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST", "other@example.com, smoke@example.com"
        )
        recipient, blocker = m8._gmail_recipient_allowed()
        assert recipient == "smoke@example.com"
        assert blocker is None

    def test_allowlist_rejects_unknown(self, monkeypatch):
        monkeypatch.setenv("M8_SMOKE_GMAIL_RECIPIENT", "nope@example.com")
        monkeypatch.setenv("M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST", "allowed@example.com")
        recipient, blocker = m8._gmail_recipient_allowed()
        assert recipient is None
        assert "allowlist" in (blocker or "").lower()


class TestGmailSmokePrompt:
    def test_prompt_has_no_destructive_language(self):
        subject, body, ask = m8._build_gmail_smoke_prompt(
            "smoke@example.com", "m8-gmail-deadbeef"
        )
        assert m8._gmail_smoke_prompt_is_safe(subject, body, ask)
        combined = f"{subject} {body} {ask}".lower()
        for word in m8._GMAIL_SMOKE_FORBIDDEN_WORDS:
            assert word not in combined

    def test_prompt_targets_send_email_not_destructive_crm(self):
        subject, body, ask = m8._build_gmail_smoke_prompt(
            "smoke@example.com", "m8-gmail-deadbeef"
        )
        assert m8._gmail_smoke_ask_targets_send_email(ask)
        assert m8._gmail_smoke_not_destructive_crm_intent(subject, body, ask)

    def test_forbidden_word_rejected(self):
        subject, body, ask = m8._build_gmail_smoke_prompt(
            "smoke@example.com", "m8-gmail-deadbeef"
        )
        assert not m8._gmail_smoke_prompt_is_safe(subject, body + " delete this", ask)


class TestCalendarProviderMatch:
    def test_external_matches_summary_and_start(self):
        fetched = {
            "id": "evt_1",
            "summary": "M8 smoke internal 2026-09-05",
            "start": "2026-09-05T15:00:00Z",
            "status": "confirmed",
        }
        assert m8._calendar_provider_matches(
            fetched,
            google_id="evt_1",
            title="M8 smoke internal 2026-09-05",
            start_iso="2026-09-05T15:00:00+00:00",
        )

    def test_external_rejects_wrong_id(self):
        assert not m8._calendar_provider_matches(
            {"id": "other", "summary": "x", "start": "2026-09-05T15:00:00Z"},
            google_id="evt_1",
            title="x",
            start_iso="2026-09-05T15:00:00+00:00",
        )


class TestCalendarInternalBookingContract:
    def test_db_matches_marker_notes_and_times(self):
        row = {
            "id": "appt-1",
            "google_event_id": "g_evt_1",
            "notes": "M8 smoke internal m8-cal-abc12345",
            "start_time": "2026-09-05T15:00:00+00:00",
            "end_time": "2026-09-05T16:00:00+00:00",
        }
        assert m8._calendar_internal_db_matches(
            row,
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
            google_id="g_evt_1",
        )

    def test_db_rejects_missing_marker(self):
        row = {
            "id": "appt-1",
            "google_event_id": "g_evt_1",
            "notes": "unrelated appointment",
            "start_time": "2026-09-05T15:00:00+00:00",
            "end_time": "2026-09-05T16:00:00+00:00",
        }
        assert not m8._calendar_internal_db_matches(
            row,
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
            google_id="g_evt_1",
        )

    def test_provider_readback_accepts_booking_summary_and_description(self):
        fetched = {
            "id": "g_evt_1",
            "summary": "Appointment with Customer",
            "description": "Customer: Customer\nEmail: noreply@agentnexlify.local\nNotes: M8 smoke internal m8-cal-abc12345",
            "start": "2026-09-05T15:00:00Z",
            "end": "2026-09-05T16:00:00Z",
            "status": "confirmed",
        }
        assert m8._calendar_internal_provider_readback_matches(
            fetched,
            google_id="g_evt_1",
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            expected_summary="Appointment with Customer",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
        )

    def test_provider_readback_rejects_wrong_summary(self):
        fetched = {
            "id": "g_evt_1",
            "summary": "M8 smoke internal m8-cal-abc12345",
            "description": "Notes: M8 smoke internal m8-cal-abc12345",
            "start": "2026-09-05T15:00:00Z",
            "end": "2026-09-05T16:00:00Z",
        }
        assert not m8._calendar_internal_provider_readback_matches(
            fetched,
            google_id="g_evt_1",
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            expected_summary="Appointment with Customer",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
        )

    def test_provider_readback_rejects_missing_marker_in_description(self):
        fetched = {
            "id": "g_evt_1",
            "summary": "Appointment with Customer",
            "description": "Customer: Customer",
            "start": "2026-09-05T15:00:00Z",
            "end": "2026-09-05T16:00:00Z",
        }
        assert not m8._calendar_internal_provider_readback_matches(
            fetched,
            google_id="g_evt_1",
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            expected_summary="Appointment with Customer",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
        )

    def test_unknown_lookup_state_fails_readback(self):
        lookup = {"state": "unknown", "reason": "api_error"}
        internal_event = lookup.get("event")
        readback_ok = lookup.get("state") == "found" and m8._calendar_internal_provider_readback_matches(
            internal_event,
            google_id="g_evt_1",
            marker="m8-cal-abc12345",
            title="M8 smoke internal m8-cal-abc12345",
            expected_summary="Appointment with Customer",
            start_iso="2026-09-05T15:00:00+00:00",
            end_iso="2026-09-05T16:00:00+00:00",
        )
        assert lookup.get("state") == "unknown"
        assert readback_ok is False


class TestExecutionMarkerMatch:
    def test_finds_marker_in_input(self):
        row = {"input": {"subject": "M8 smoke m8-gmail-deadbeef"}}
        assert m8._execution_input_contains(row, "m8-gmail-deadbeef")


class TestSendOnlyGmailProofHelpers:
    def test_pending_not_sent_requires_pending_status(self):
        row = {"status": "succeeded", "result": {}}
        assert m8._send_email_pending_not_sent(row) is False

    def test_pending_not_sent_rejects_existing_provider_id(self):
        row = {
            "status": "pending_approval",
            "result": {"messageId": "gm_123"},
        }
        assert m8._send_email_pending_not_sent(row) is False

    def test_pending_not_sent_passes_clean_pending_row(self):
        row = {"status": "pending_approval", "result": None}
        assert m8._send_email_pending_not_sent(row) is True

    def test_payload_matches_approved_fields(self):
        row = {
            "input": {
                "to": "smoke@example.com",
                "subject": "M8 smoke m8-gmail-abc",
                "body": (
                    "Milestone 8 controlled test message m8-gmail-abc. "
                    "No follow-up action is required."
                ),
            }
        }
        assert m8._send_payload_matches(
            row,
            "smoke@example.com",
            "M8 smoke m8-gmail-abc",
            (
                "Milestone 8 controlled test message m8-gmail-abc. "
                "No follow-up action is required."
            ),
            "m8-gmail-abc",
        )

    def test_provider_message_id_from_result(self):
        row = {"result": {"messageId": "186abc"}}
        assert m8._provider_message_id_from_execution(row) == "186abc"


class TestCalendarCancelLookup:
    def test_not_found_proves_deleted(self):
        assert m8._cancel_lookup_proves_deleted({"state": "not_found"}) is True

    def test_found_cancelled_proves_deleted(self):
        assert m8._cancel_lookup_proves_deleted(
            {"state": "found", "event": {"status": "cancelled"}}
        )

    def test_unknown_does_not_prove_deleted(self):
        assert m8._cancel_lookup_proves_deleted({"state": "unknown"}) is False

    def test_found_confirmed_does_not_prove_deleted(self):
        assert m8._cancel_lookup_proves_deleted(
            {"state": "found", "event": {"status": "confirmed"}}
        ) is False


class TestProviderEventCountUnknown:
    def test_unknown_lookup_is_not_zero(self, monkeypatch):
        from datetime import datetime, timezone

        import backend.services.google_calendar as gcal

        def _fake_list(*_a, **_k):
            return {"state": "unknown", "reason": "api_error", "events": []}

        monkeypatch.setattr(gcal, "list_calendar_events_in_window", _fake_list)
        now = datetime.now(timezone.utc)
        state, count = m8._provider_events_matching_marker(
            "tenant", "m8-ext-abc", now, now
        )
        assert state == "unknown"
        assert count == -1
