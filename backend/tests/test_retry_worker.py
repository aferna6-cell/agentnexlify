"""Tests for the pending_automations retry worker (issue #118).

App-free: injects a filtering FakeDB + async dispatchers, so no Supabase/app
boot is needed.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from backend.services import retry_worker as rw

_NOW = datetime(2026, 7, 21, tzinfo=timezone.utc)


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, db):
        self.db = db
        self.mode = None
        self.filters = {}
        self._lte = None
        self.payload = None

    def select(self, *_a):
        self.mode = "select"
        return self

    def eq(self, k, v):
        self.filters[k] = v
        return self

    def lte(self, k, v):
        self._lte = (k, v)
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def execute(self):
        if self.mode == "update":
            self.db.updates.append((self.filters.get("id"), self.payload))
            return _Result([])
        rows = []
        for r in self.db.rows:
            ok = all(r.get(k) == v for k, v in self.filters.items())
            if self._lte:
                k, v = self._lte
                ok = ok and (r.get(k) is not None and r.get(k) <= v)
            if ok:
                rows.append(r)
        return _Result(rows)


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []  # list of (row_id, payload) — observable state

    def table(self, _name):
        return _FakeTable(self)


def _row(rid, atype="missed_call_text", retry_count=0, scheduled_days_ago=1):
    return {
        "id": rid,
        "tenant_id": "t1",
        "automation_type": atype,
        "payload_json": {"n": 1},
        "status": "pending",
        "retry_count": retry_count,
        "scheduled_for": (_NOW - timedelta(days=scheduled_days_ago)).isoformat(),
    }


async def _ok(_tenant, _payload):
    return True


async def _fail(_tenant, _payload):
    return False


def test_exponential_backoff_schedule():
    assert rw.BACKOFF_SECONDS == (30, 120, 600)
    assert rw.MAX_ATTEMPTS == 3
    assert rw.next_scheduled_for(1, _NOW) == _NOW + timedelta(seconds=30)
    assert rw.next_scheduled_for(2, _NOW) == _NOW + timedelta(seconds=120)


def test_drain_skips_future_scheduled():
    due = _row("due", scheduled_days_ago=1)
    future = dict(_row("future"), scheduled_for=(_NOW + timedelta(days=1)).isoformat())
    db = _FakeDB([due, future])
    processed = asyncio.run(
        rw.drain_pending_automations(now=_NOW, db=db, dispatchers={"missed_call_text": _ok})
    )
    assert processed == 1  # only the due row
    assert [u[0] for u in db.updates] == ["due"]  # future row never touched


def test_drain_executes_due_items_marks_done():
    db = _FakeDB([_row("a"), _row("b")])
    processed = asyncio.run(
        rw.drain_pending_automations(now=_NOW, db=db, dispatchers={"missed_call_text": _ok})
    )
    assert processed == 2
    assert all(payload == {"status": "done"} for _id, payload in db.updates)


def test_failure_increments_retry_count_and_reschedules():
    db = _FakeDB([_row("a", retry_count=0)])
    asyncio.run(
        rw.drain_pending_automations(now=_NOW, db=db, dispatchers={"missed_call_text": _fail})
    )
    _id, payload = db.updates[0]
    assert payload["status"] == "pending"
    assert payload["retry_count"] == 1
    assert payload["scheduled_for"] == (_NOW + timedelta(seconds=30)).isoformat()


def test_third_failure_marks_failed():
    db = _FakeDB([_row("a", retry_count=2)])  # this attempt makes it 3
    asyncio.run(
        rw.drain_pending_automations(now=_NOW, db=db, dispatchers={"missed_call_text": _fail})
    )
    _id, payload = db.updates[0]
    assert payload == {"status": "failed", "retry_count": 3}


def test_missing_dispatcher_treated_as_failure():
    db = _FakeDB([_row("a", atype="unknown_type", retry_count=0)])
    asyncio.run(rw.drain_pending_automations(now=_NOW, db=db, dispatchers={}))
    _id, payload = db.updates[0]
    assert payload["status"] == "pending" and payload["retry_count"] == 1


def test_query_failure_is_fail_open():
    class _BoomDB:
        def table(self, _n):
            raise RuntimeError("table missing (migration 180 unapplied)")

    processed = asyncio.run(rw.drain_pending_automations(now=_NOW, db=_BoomDB()))
    assert processed == 0  # never raises
