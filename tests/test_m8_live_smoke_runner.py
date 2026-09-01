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


class TestCalendarProviderMatch:
    def test_matches_summary_and_start(self):
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

    def test_rejects_wrong_id(self):
        assert not m8._calendar_provider_matches(
            {"id": "other", "summary": "x", "start": "2026-09-05T15:00:00Z"},
            google_id="evt_1",
            title="x",
            start_iso="2026-09-05T15:00:00+00:00",
        )


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
                "body": "Milestone 8 controlled send m8-gmail-abc — safe to delete.",
            }
        }
        assert m8._send_payload_matches(
            row,
            "smoke@example.com",
            "M8 smoke m8-gmail-abc",
            "Milestone 8 controlled send m8-gmail-abc — safe to delete.",
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
