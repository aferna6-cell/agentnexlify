"""Unit tests for M8 live smoke runner helpers (no staging I/O)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

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
