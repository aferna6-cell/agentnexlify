"""Tests for the durable retry worker (Phase 4).

Covers backend/services/retry_worker.py:
  - BACKOFF_SECONDS / MAX_ATTEMPTS contract (30s / 2min / 10min, 3 attempts)
  - enqueue_pending_automation inserts a pending row scheduled in the future
  - drain: handler success -> status='done'
  - drain: handler failure -> retry_count incremented + rescheduled with backoff
  - drain: final attempt failure -> status='failed' (stuck, surfaced via /pending)
  - drain: unknown automation_type -> status='failed'
  - Sentry breadcrumb emitted on each attempt
  - filter_stuck_pending: failed rows + pending rows older than 1h

The Supabase client is replaced with a small in-memory fake that records
inserts/updates and replays a canned select result. No network, no ASGI.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.services import retry_worker


# ---------------------------------------------------------------------------
# In-memory Supabase fake
# ---------------------------------------------------------------------------
class _FakeQuery:
    def __init__(self, table):
        self._table = table
        self._select_rows = table._rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def lte(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, row):
        self._table.inserted.append(row)
        return self

    def update(self, fields):
        self._table._pending_update = dict(fields)
        return self

    def execute(self):
        if self._table._pending_update is not None:
            self._table.updates.append(self._table._pending_update)
            self._table._pending_update = None
            return _Result([])
        return _Result(list(self._table._rows))


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, rows):
        self._rows = rows
        self.inserted = []
        self.updates = []
        self._pending_update = None

    # _FakeQuery shares state with the table
    def __getattr__(self, name):
        return getattr(_FakeQuery(self), name)


class _FakeDB:
    def __init__(self, rows):
        self._table = _FakeTable(rows)

    def table(self, _name):
        return self._table


def _install_fake_db(monkeypatch, rows):
    db = _FakeDB(rows)
    monkeypatch.setattr(retry_worker, "get_service_supabase", lambda: db)
    return db


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
def test_backoff_schedule_matches_spec():
    # spec: 30s, 2min, 10min — 3 attempts
    assert retry_worker.BACKOFF_SECONDS == [30, 120, 600]
    assert retry_worker.MAX_ATTEMPTS == 3


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------
def test_enqueue_inserts_pending_row(monkeypatch):
    db = _install_fake_db(monkeypatch, [])
    retry_worker.enqueue_pending_automation(
        "tenant-1", "missed_call_text", {"to_phone": "+15551234567"}
    )
    assert len(db._table.inserted) == 1
    row = db._table.inserted[0]
    assert row["tenant_id"] == "tenant-1"
    assert row["automation_type"] == "missed_call_text"
    assert row["status"] == "pending"
    assert row["retry_count"] == 0
    assert row["payload_json"] == {"to_phone": "+15551234567"}
    # scheduled_for is in the future
    sched = datetime.fromisoformat(row["scheduled_for"])
    assert sched > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# drain
# ---------------------------------------------------------------------------
def _make_row(retry_count=0, automation_type="t_ok"):
    return {
        "id": "row-1",
        "tenant_id": "tenant-1",
        "automation_type": automation_type,
        "payload_json": {"x": 1},
        "retry_count": retry_count,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def test_drain_success_marks_done(monkeypatch):
    db = _install_fake_db(monkeypatch, [_make_row(automation_type="t_ok")])

    async def _ok(_payload):
        return True

    monkeypatch.setattr(retry_worker, "_HANDLERS", {"t_ok": _ok})
    _run(retry_worker.drain_pending_automations())

    statuses = [u.get("status") for u in db._table.updates if "status" in u]
    assert statuses[-1] == "done"


def test_drain_failure_reschedules_with_backoff(monkeypatch):
    db = _install_fake_db(
        monkeypatch, [_make_row(retry_count=0, automation_type="t_fail")]
    )

    async def _fail(_payload):
        return False

    monkeypatch.setattr(retry_worker, "_HANDLERS", {"t_fail": _fail})
    _run(retry_worker.drain_pending_automations())

    # last update reschedules: status back to pending, retry_count=1
    final = db._table.updates[-1]
    assert final["status"] == "pending"
    assert final["retry_count"] == 1
    sched = datetime.fromisoformat(final["scheduled_for"])
    # attempt 1 -> BACKOFF_SECONDS[1] == 120s
    delta = (sched - datetime.now(timezone.utc)).total_seconds()
    assert 60 < delta <= 130


def test_drain_final_attempt_marks_failed(monkeypatch):
    # retry_count already at MAX-1 -> next failure is terminal
    db = _install_fake_db(
        monkeypatch, [_make_row(retry_count=2, automation_type="t_fail")]
    )

    async def _fail(_payload):
        return False

    monkeypatch.setattr(retry_worker, "_HANDLERS", {"t_fail": _fail})
    _run(retry_worker.drain_pending_automations())

    final = db._table.updates[-1]
    assert final["status"] == "failed"
    assert final["retry_count"] == 3


def test_drain_unknown_type_marks_failed(monkeypatch):
    db = _install_fake_db(monkeypatch, [_make_row(automation_type="nope")])
    monkeypatch.setattr(retry_worker, "_HANDLERS", {})
    _run(retry_worker.drain_pending_automations())
    final = db._table.updates[-1]
    assert final["status"] == "failed"


def test_drain_emits_sentry_breadcrumb(monkeypatch):
    _install_fake_db(monkeypatch, [_make_row(automation_type="t_ok")])
    crumbs = []
    monkeypatch.setattr(retry_worker, "_sentry_breadcrumb", lambda *a: crumbs.append(a))

    async def _ok(_payload):
        return True

    monkeypatch.setattr(retry_worker, "_HANDLERS", {"t_ok": _ok})
    _run(retry_worker.drain_pending_automations())
    assert len(crumbs) == 1


# ---------------------------------------------------------------------------
# filter_stuck_pending
# ---------------------------------------------------------------------------
def test_filter_stuck_pending():
    now = datetime.now(timezone.utc)
    old_pending = {
        "id": "a",
        "status": "pending",
        "created_at": (now - timedelta(hours=2)).isoformat(),
    }
    fresh_pending = {
        "id": "b",
        "status": "pending",
        "created_at": (now - timedelta(minutes=5)).isoformat(),
    }
    failed = {
        "id": "c",
        "status": "failed",
        "created_at": (now - timedelta(minutes=1)).isoformat(),
    }
    stuck = retry_worker.filter_stuck_pending(
        [old_pending, fresh_pending, failed], now=now
    )
    ids = {r["id"] for r in stuck}
    assert ids == {"a", "c"}  # old pending + failed; fresh pending excluded


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
