"""Appointment briefs + follow-up drafts — context assembly and parsing.

Claude calls are stubbed; these tests cover the deterministic parts:
context gathering (including the no-history path), subject splitting, and
the approval-first response shape.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.fake_supabase import db, run

from backend.services import appointment_brief
from backend.services.appointment_brief import (
    AppointmentBriefError,
    _split_subject,
    gather_context,
)

_APPT = {
    "id": "a1",
    "customer_name": "Cara Diaz",
    "customer_email": "cara@example.com",
    "customer_phone": None,
    "start_time": "2026-08-06T15:00:00Z",
    "end_time": "2026-08-06T16:00:00Z",
    "status": "confirmed",
    "notes": "Prefers afternoon",
    "lead_id": "l1",
}

_LEAD = {
    "id": "l1",
    "name": "Cara Diaz",
    "email": "cara@example.com",
    "phone": None,
    "status": "qualified",
    "areas_of_interest": "kitchen remodel",
    "conversation_summary": "Wants a quote for a kitchen remodel.",
    "conversation_id": "c1",
    "created_at": "2026-08-01",
}

_CONV = {"messages": [
    {"role": "user", "content": "Hi, do you do kitchen remodels?"},
    {"role": "assistant", "content": "We do! Want to book a consult?"},
]}


def test_gather_context_missing_appointment_raises():
    with pytest.raises(AppointmentBriefError):
        gather_context(db({}), "t1", "a-missing")


def test_gather_context_full_chain():
    fixture = db({"appointments": [_APPT], "leads": [_LEAD], "conversations": [_CONV]})
    ctx = gather_context(fixture, "t1", "a1")
    assert ctx["appointment"]["customer_name"] == "Cara Diaz"
    assert ctx["lead"]["areas_of_interest"] == "kitchen remodel"
    assert "kitchen remodels?" in ctx["transcript"]
    assert "Visitor:" in ctx["transcript"] and "Agent:" in ctx["transcript"]


def test_gather_context_walk_in_without_lead():
    """A booking with no linked lead still yields a usable context."""
    walk_in = {**_APPT, "lead_id": None}
    ctx = gather_context(db({"appointments": [walk_in]}), "t1", "a1")
    assert ctx["lead"] == {}
    assert ctx["transcript"] == ""


def test_split_subject_parses_subject_line():
    subject, body = _split_subject("Subject: Thanks for coming in\n\nGreat to meet you.")
    assert subject == "Thanks for coming in"
    assert body == "Great to meet you."


def test_split_subject_tolerates_missing_subject():
    subject, body = _split_subject("Great to meet you.")
    assert subject == "Following up on your appointment"
    assert body == "Great to meet you."


def _stub_claude(monkeypatch, text):
    async def fake_call(**kwargs):
        result = MagicMock()
        result.text = text
        return result

    monkeypatch.setattr(appointment_brief, "call_claude_messages", fake_call)


def test_generate_brief_reports_history_flag(monkeypatch):
    _stub_claude(monkeypatch, "## Who they are\nCara.")
    fixture = db({"appointments": [_APPT], "leads": [_LEAD], "conversations": [_CONV]})
    out = run(appointment_brief.generate_brief(fixture, "t1", "a1", "Acme"))
    assert out["brief"].startswith("## Who they are")
    assert out["has_history"] is True


def test_draft_followup_returns_draft_never_sends(monkeypatch):
    _stub_claude(monkeypatch, "Subject: Great seeing you\n\nThanks for stopping by!")
    sink = []
    fixture = db(
        {"appointments": [_APPT], "leads": [_LEAD], "conversations": [_CONV]}, sink
    )
    out = run(appointment_brief.draft_followup(fixture, "t1", "a1", "Acme"))
    assert out["subject"] == "Great seeing you"
    assert out["body"] == "Thanks for stopping by!"
    assert out["customer_email"] == "cara@example.com"
    # approval-first: reads only — no insert/update/delete touched any table
    mutating = [c for c in sink if c[1] in ("insert", "update", "delete")]
    assert mutating == []
