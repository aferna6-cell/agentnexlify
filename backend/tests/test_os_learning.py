"""Unit tests for os_learning — the action -> outcome -> memory loop.

Spec: agent-os-north-star gap #2 (the "Learn" verb).

Design (deterministic-first):
- After a lead-targeting action succeeds (email.send / sms.send /
  calendar.event.create), record a *pending* os_action_outcomes row keyed to
  the resolved lead. Recipient -> lead is a deterministic join
  (email/attendee_email -> leads.email, sms to -> leads.phone). No lead match
  -> skip (lead-targeting only).
- A pending row settles after RESOLVE_WINDOW_DAYS (3). At settle time the
  outcome is computed deterministically with the ladder booked > converted >
  no_response:
    * booked    — an appointment for this lead created after sent_at
    * converted — lead.status is now 'closed' and was not 'closed' at send
    * no_response — neither, once the window elapses
- Exactly one os_memory_entries row (kind='outcome') is written per resolved
  outcome so the orchestrator's search_memory recalls it next turn.

Focus:
- recipient resolution per action type
- settle window = sent_at + 3 days
- pending-row capture: lead hit writes a row, lead miss skips
- outcome ladder branches
- single memory write on resolve, kind='outcome'
- idempotent resolve: only status='pending' rows are picked up
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import backend.services.os_learning as learn
from backend.services.os_learning import (
    RESOLVE_WINDOW_DAYS,
    _resolve_recipient,
    _settle_by,
    _summarize_outcome,
    record_action_outcome_pending,
    resolve_due_outcomes,
)

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_RUN_ID = "11111111-1111-1111-1111-111111111111"
_LEAD_ID = "22222222-2222-2222-2222-222222222222"


# ---------------------------------------------------------------------------
# Fake Supabase — per-table results + an insert log (multi-query friendly).
# ---------------------------------------------------------------------------


class _FakeQuery:
    def __init__(self, table_name, results, inserts):
        self.table_name = table_name
        self._results = results
        self._inserts = inserts
        self._last_insert = None

    def select(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def delete(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def lte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def insert(self, payload):
        self._last_insert = payload
        self._inserts.append((self.table_name, payload))
        return self

    def execute(self):
        if self._last_insert is not None:
            row = dict(self._last_insert)
            row.setdefault("id", "generated-id")
            return SimpleNamespace(data=[row])
        return SimpleNamespace(data=list(self._results.get(self.table_name, [])))


class _FakeDB:
    """db.table(name) -> query whose execute() returns results[name]."""

    def __init__(self, results=None):
        self.results = results or {}
        self.inserts = []

    def table(self, name):
        return _FakeQuery(name, self.results, self.inserts)

    def inserts_into(self, table_name):
        return [p for (t, p) in self.inserts if t == table_name]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_resolve_recipient_email_action_uses_to():
    assert _resolve_recipient("email.send", {"to": "a@b.com"}) == "a@b.com"


def test_resolve_recipient_sms_action_uses_to():
    assert _resolve_recipient("sms.send", {"to": "+15555550123"}) == "+15555550123"


def test_resolve_recipient_calendar_action_uses_attendee_email():
    assert (
        _resolve_recipient("calendar.event.create", {"attendee_email": "c@d.com"})
        == "c@d.com"
    )


def test_resolve_recipient_calendar_null_attendee_returns_none():
    assert _resolve_recipient("calendar.event.create", {"attendee_email": None}) is None


def test_resolve_recipient_unknown_action_returns_none():
    assert _resolve_recipient("gbp.post.create", {"to": "x"}) is None


def test_settle_window_is_three_days():
    assert RESOLVE_WINDOW_DAYS == 3


def test_settle_by_adds_window():
    settle = _settle_by("2026-06-01T00:00:00+00:00")
    assert settle.startswith("2026-06-04T00:00:00")


def test_summarize_outcome_names_action_lead_and_outcome():
    text = _summarize_outcome(
        action_type="email.send",
        recipient="alice@example.com",
        lead_name="Alice",
        lead_status_at_send="contacted",
        outcome="booked",
    )
    assert "email.send" in text
    assert "Alice" in text
    assert "booked" in text
    assert "contacted" in text


# ---------------------------------------------------------------------------
# record_action_outcome_pending — capture
# ---------------------------------------------------------------------------


def test_record_writes_pending_row_for_email_lead_hit():
    db = _FakeDB(
        results={"leads": [{"id": _LEAD_ID, "name": "Alice", "status": "contacted"}]}
    )
    row = asyncio.run(
        record_action_outcome_pending(
            db,
            _CLIENT_A,
            _RUN_ID,
            "email.send",
            {"to": "alice@example.com", "subject": "Hi", "body_html": "<p>hi</p>"},
            sent_at="2026-06-01T00:00:00+00:00",
        )
    )
    assert row is not None
    written = db.inserts_into("os_action_outcomes")
    assert len(written) == 1
    payload = written[0]
    assert payload["action_run_id"] == _RUN_ID
    assert payload["action_type"] == "email.send"
    assert payload["lead_id"] == _LEAD_ID
    assert payload["recipient"] == "alice@example.com"
    assert payload["lead_status_at_send"] == "contacted"
    assert payload["status"] == "pending"
    assert payload["settle_by"].startswith("2026-06-04")


def test_record_resolves_sms_recipient_against_phone():
    db = _FakeDB(results={"leads": [{"id": _LEAD_ID, "name": "Bob", "status": "new"}]})
    row = asyncio.run(
        record_action_outcome_pending(
            db,
            _CLIENT_A,
            _RUN_ID,
            "sms.send",
            {"to": "+15555550123", "body": "hey"},
            sent_at="2026-06-01T00:00:00+00:00",
        )
    )
    assert row is not None
    payload = db.inserts_into("os_action_outcomes")[0]
    assert payload["recipient"] == "+15555550123"
    assert payload["lead_id"] == _LEAD_ID


def test_record_skips_when_no_lead_matches():
    db = _FakeDB(results={"leads": []})
    row = asyncio.run(
        record_action_outcome_pending(
            db,
            _CLIENT_A,
            _RUN_ID,
            "email.send",
            {"to": "stranger@example.com"},
            sent_at="2026-06-01T00:00:00+00:00",
        )
    )
    assert row is None
    assert db.inserts_into("os_action_outcomes") == []


def test_record_skips_when_recipient_unresolvable():
    db = _FakeDB(results={"leads": [{"id": _LEAD_ID, "status": "new"}]})
    row = asyncio.run(
        record_action_outcome_pending(
            db,
            _CLIENT_A,
            _RUN_ID,
            "calendar.event.create",
            {"summary": "Call", "attendee_email": None},
            sent_at="2026-06-01T00:00:00+00:00",
        )
    )
    assert row is None
    assert db.inserts_into("os_action_outcomes") == []


# ---------------------------------------------------------------------------
# _compute_outcome — the deterministic ladder
# ---------------------------------------------------------------------------


def _pending_row(**over):
    base = {
        "id": "out-1",
        "action_run_id": _RUN_ID,
        "action_type": "email.send",
        "lead_id": _LEAD_ID,
        "recipient": "alice@example.com",
        "lead_status_at_send": "contacted",
        "sent_at": "2026-06-01T00:00:00+00:00",
        "settle_by": "2026-06-04T00:00:00+00:00",
        "status": "pending",
    }
    base.update(over)
    return base


def test_compute_outcome_booked_when_appointment_after_send():
    db = _FakeDB(
        results={
            "appointments": [
                {"id": "appt-1", "created_at": "2026-06-02T00:00:00+00:00"}
            ],
            "leads": [{"id": _LEAD_ID, "status": "appointment_booked"}],
        }
    )
    outcome = asyncio.run(learn._compute_outcome(db, _CLIENT_A, _pending_row()))
    assert outcome == "booked"


def test_compute_outcome_converted_when_status_now_closed():
    db = _FakeDB(
        results={
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "status": "closed"}],
        }
    )
    outcome = asyncio.run(learn._compute_outcome(db, _CLIENT_A, _pending_row()))
    assert outcome == "converted"


def test_compute_outcome_not_converted_when_already_closed_at_send():
    db = _FakeDB(
        results={
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "status": "closed"}],
        }
    )
    outcome = asyncio.run(
        learn._compute_outcome(
            db, _CLIENT_A, _pending_row(lead_status_at_send="closed")
        )
    )
    assert outcome == "no_response"


def test_compute_outcome_no_response_default():
    db = _FakeDB(
        results={
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "status": "contacted"}],
        }
    )
    outcome = asyncio.run(learn._compute_outcome(db, _CLIENT_A, _pending_row()))
    assert outcome == "no_response"


def test_compute_outcome_booked_beats_converted():
    db = _FakeDB(
        results={
            "appointments": [
                {"id": "appt-1", "created_at": "2026-06-02T00:00:00+00:00"}
            ],
            "leads": [{"id": _LEAD_ID, "status": "closed"}],
        }
    )
    outcome = asyncio.run(learn._compute_outcome(db, _CLIENT_A, _pending_row()))
    assert outcome == "booked"


# ---------------------------------------------------------------------------
# resolve_due_outcomes — settle, write memory, mark resolved
# ---------------------------------------------------------------------------


def test_resolve_writes_single_outcome_memory_and_marks_resolved():
    db = _FakeDB(
        results={
            "os_action_outcomes": [_pending_row()],
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "name": "Alice", "status": "contacted"}],
        }
    )
    with patch.object(learn, "embed_text", new=AsyncMock(return_value=[0.0] * 512)):
        outcomes = asyncio.run(resolve_due_outcomes(_CLIENT_A, db))

    assert len(outcomes) == 1
    assert outcomes[0]["outcome"] == "no_response"

    mem = db.inserts_into("os_memory_entries")
    assert len(mem) == 1, "exactly one memory entry per resolved outcome"
    assert mem[0]["kind"] == "outcome"
    assert "no_response" in mem[0]["content"]


def test_resolve_marks_memory_with_source_ref_for_dedup():
    db = _FakeDB(
        results={
            "os_action_outcomes": [_pending_row()],
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "name": "Alice", "status": "contacted"}],
        }
    )
    with patch.object(learn, "embed_text", new=AsyncMock(return_value=[0.0] * 512)):
        asyncio.run(resolve_due_outcomes(_CLIENT_A, db))
    mem = db.inserts_into("os_memory_entries")[0]
    assert mem.get("source_ref") == f"outcome:{_RUN_ID}"


def test_resolve_memory_write_survives_embed_failure():
    db = _FakeDB(
        results={
            "os_action_outcomes": [_pending_row()],
            "appointments": [],
            "leads": [{"id": _LEAD_ID, "name": "Alice", "status": "contacted"}],
        }
    )
    with patch.object(
        learn, "embed_text", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        outcomes = asyncio.run(resolve_due_outcomes(_CLIENT_A, db))
    assert len(outcomes) == 1
    mem = db.inserts_into("os_memory_entries")
    assert len(mem) == 1
    assert mem[0]["embedding"] is None


def test_resolve_returns_empty_when_no_due_rows():
    db = _FakeDB(results={"os_action_outcomes": []})
    with patch.object(learn, "embed_text", new=AsyncMock(return_value=[0.0] * 512)):
        outcomes = asyncio.run(resolve_due_outcomes(_CLIENT_A, db))
    assert outcomes == []
    assert db.inserts_into("os_memory_entries") == []
