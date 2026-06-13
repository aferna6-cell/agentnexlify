"""Unit tests for email-sequence send processing + count helpers.

Covers the two perf/refactor fixes:
- GH #112: `_count_by_sequence_id` (bulk tally) and the bulk lead fetch in
  `list_enrollments` replace per-row N+1 round-trips.
- GH #113: `process_sequences` (HTTP) and `run_sequence_processor` (standalone)
  both delegate to the shared `_process_pending_sends`, so the per-send logic is
  exercised once here and can't drift between the two callers.

The fake query-builder mimics the subset of the supabase-py fluent API the
router actually uses (`.table().select().eq().in_().lte().order().limit().execute()`
plus `.update().eq().execute()`).
"""

import asyncio

import pytest

from backend.routers import email_sequences as es


class _FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, db, table):
        self._db = db
        self._table = table
        self._filters = {}
        self._in = {}
        self._is_write = False
        self._payload = None

    def select(self, *a, **k):
        return self

    def update(self, payload):
        self._is_write = True
        self._payload = payload
        return self

    def delete(self):
        self._is_write = True
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def in_(self, col, vals):
        self._in[col] = list(vals)
        return self

    def lte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._is_write:
            self._db.writes.append((self._table, dict(self._filters), self._payload))
            return _FakeResult([])
        return self._db.resolve(self._table, self._filters, self._in)


class _FakeDB:
    def __init__(self, *, steps=None, leads=None, tenants=None,
                 step_rows=None, enroll_rows=None):
        self.steps = steps or {}            # id -> row
        self.leads = leads or {}            # id -> row
        self.tenants = tenants or {}        # id -> row
        self.step_rows = step_rows or []    # [{sequence_id: ...}, ...]
        self.enroll_rows = enroll_rows or []
        self.writes = []

    def table(self, name):
        return _FakeQuery(self, name)

    def resolve(self, table, filters, in_):
        if table == "email_sequence_steps" and "sequence_id" in in_:
            sel = in_["sequence_id"]
            return _FakeResult([r for r in self.step_rows if r["sequence_id"] in sel])
        if table == "email_sequence_enrollments" and "sequence_id" in in_:
            sel = in_["sequence_id"]
            return _FakeResult([r for r in self.enroll_rows if r["sequence_id"] in sel])
        if table == "email_sequence_steps":
            row = self.steps.get(filters.get("id"))
            return _FakeResult([row] if row else [])
        if table == "leads":
            row = self.leads.get(filters.get("id"))
            return _FakeResult([row] if row else [])
        if table == "tenants":
            row = self.tenants.get(filters.get("id"))
            return _FakeResult([row] if row else [])
        return _FakeResult([])


# --------------------------------------------------------------------------- #
# GH #112 — bulk count helper
# --------------------------------------------------------------------------- #


def test_count_by_sequence_id_tallies():
    db = _FakeDB(step_rows=[
        {"sequence_id": "a"}, {"sequence_id": "a"}, {"sequence_id": "b"},
    ])
    counts = es._count_by_sequence_id(db, "email_sequence_steps", ["a", "b", "c"])
    assert counts == {"a": 2, "b": 1}


def test_count_by_sequence_id_empty_returns_empty():
    db = _FakeDB()
    assert es._count_by_sequence_id(db, "email_sequence_steps", []) == {}


# --------------------------------------------------------------------------- #
# GH #113 — shared per-send processor
# --------------------------------------------------------------------------- #


def _due(send_id="s1", **over):
    base = {
        "id": send_id,
        "step_id": "step1",
        "lead_id": "lead1",
        "tenant_id": "ten1",
        "enrollment_id": "enr1",
    }
    base.update(over)
    return base


def _patch_send(monkeypatch, *, success=True, detail="boom"):
    async def _fake_send_email(**kwargs):
        return {"success": success, "detail": detail}

    monkeypatch.setattr(es, "send_email", _fake_send_email)
    monkeypatch.setattr(es, "render_template", lambda tmpl, ctx: tmpl)
    monkeypatch.setattr(es, "build_unsubscribe_url", lambda lead, ten: "http://u")
    monkeypatch.setattr(es, "log_activity", lambda **k: None)
    monkeypatch.setattr(es, "_increment_runs_total", lambda *a, **k: None)
    monkeypatch.setattr(es, "_maybe_complete_enrollment", lambda *a, **k: None)


def test_process_pending_sends_happy_path(monkeypatch):
    _patch_send(monkeypatch, success=True)
    db = _FakeDB(
        steps={"step1": {"subject": "Hi", "body": "B", "step_order": 1, "sequence_id": "seq1"}},
        leads={"lead1": {"id": "lead1", "name": "Ana", "email": "a@x.com", "unsubscribed": False}},
        tenants={"ten1": {"business_name": "Biz"}},
    )
    res = asyncio.run(es._process_pending_sends(db, [_due()]))
    assert res == {"processed": 1, "sent": 1, "failed": 0, "skipped": 0}
    # send marked 'sent'
    assert any(t == "email_sequence_sends" and p.get("status") == "sent"
               for (t, _f, p) in db.writes)


def test_process_pending_sends_unsubscribed_skips(monkeypatch):
    _patch_send(monkeypatch, success=True)
    db = _FakeDB(
        steps={"step1": {"subject": "Hi", "body": "B", "step_order": 1, "sequence_id": "seq1"}},
        leads={"lead1": {"id": "lead1", "name": "Ana", "email": "a@x.com", "unsubscribed": True}},
        tenants={"ten1": {"business_name": "Biz"}},
    )
    res = asyncio.run(es._process_pending_sends(db, [_due()]))
    assert res == {"processed": 1, "sent": 0, "failed": 0, "skipped": 1}
    assert any(p.get("error") == "unsubscribed" for (_t, _f, p) in db.writes)


def test_process_pending_sends_no_email_skips(monkeypatch):
    _patch_send(monkeypatch, success=True)
    db = _FakeDB(
        steps={"step1": {"subject": "Hi", "body": "B", "step_order": 1, "sequence_id": "seq1"}},
        leads={"lead1": {"id": "lead1", "name": "Ana", "email": "", "unsubscribed": False}},
        tenants={"ten1": {"business_name": "Biz"}},
    )
    res = asyncio.run(es._process_pending_sends(db, [_due()]))
    assert res["skipped"] == 1 and res["sent"] == 0


def test_process_pending_sends_missing_step_skips(monkeypatch):
    _patch_send(monkeypatch, success=True)
    db = _FakeDB(leads={"lead1": {"id": "lead1", "email": "a@x.com"}})
    res = asyncio.run(es._process_pending_sends(db, [_due()]))
    assert res == {"processed": 1, "sent": 0, "failed": 0, "skipped": 1}


def test_process_pending_sends_send_failure_counts_failed(monkeypatch):
    _patch_send(monkeypatch, success=False, detail="provider down")
    db = _FakeDB(
        steps={"step1": {"subject": "Hi", "body": "B", "step_order": 1, "sequence_id": "seq1"}},
        leads={"lead1": {"id": "lead1", "name": "Ana", "email": "a@x.com", "unsubscribed": False}},
        tenants={"ten1": {"business_name": "Biz"}},
    )
    res = asyncio.run(es._process_pending_sends(db, [_due()]))
    assert res == {"processed": 1, "sent": 0, "failed": 1, "skipped": 0}
    assert any(p.get("error") == "provider down" for (_t, _f, p) in db.writes)


# --------------------------------------------------------------------------- #
# GH #113 — both callers delegate to the shared processor
# --------------------------------------------------------------------------- #


def test_run_sequence_processor_delegates(monkeypatch):
    sentinel = {"processed": 3, "sent": 2, "failed": 1, "skipped": 0}
    seen = {}

    async def _fake_proc(db, due):
        seen["due"] = due
        return sentinel

    monkeypatch.setattr(es, "get_service_supabase", lambda: _FakeDB())
    monkeypatch.setattr(es, "_query_due_sends", lambda db: [_due("s9")])
    monkeypatch.setattr(es, "_process_pending_sends", _fake_proc)

    res = asyncio.run(es.run_sequence_processor())
    assert res == sentinel
    assert seen["due"] == [_due("s9")]


def test_process_sequences_endpoint_delegates(monkeypatch):
    sentinel = {"processed": 1, "sent": 1, "failed": 0, "skipped": 0}

    async def _fake_proc(db, due):
        return sentinel

    monkeypatch.setattr(es, "get_service_supabase", lambda: _FakeDB())
    monkeypatch.setattr(es, "_query_due_sends", lambda db: [_due()])
    monkeypatch.setattr(es, "_process_pending_sends", _fake_proc)
    monkeypatch.setattr(es.settings, "api_secret_key", "secret")

    res = asyncio.run(es.process_sequences(x_internal_key="secret"))
    assert res == sentinel


def test_process_sequences_endpoint_rejects_bad_key(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(es.settings, "api_secret_key", "secret")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(es.process_sequences(x_internal_key="wrong"))
    assert exc.value.status_code == 401
