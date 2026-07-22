"""Tests for the pending_automations retry drainer (#118).

Stateful faked db (rows mutate in place so final state is assertable):
    python3 -m pytest backend/tests/test_retry_worker.py -v --noconftest
"""

from datetime import datetime, timedelta, timezone

from backend.services import retry_worker as rw


# --------------------------------------------------------------------------- #
# Stateful fake Supabase                                                       #
# --------------------------------------------------------------------------- #
class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, fail):
        self._rows = rows
        self._fail = fail
        self._filters = {}
        self._update = None

    def select(self, *a, **k):
        return self

    def update(self, fields):
        self._update = fields
        return self

    def eq(self, col, val):
        self._filters[col] = ("eq", val)
        return self

    def lte(self, col, val):
        self._filters[col] = ("lte", val)
        return self

    def _match(self, row):
        for col, (op, val) in self._filters.items():
            cur = row.get(col)
            if op == "eq" and cur != val:
                return False
            if op == "lte" and not (cur is not None and cur <= val):
                return False
        return True

    def execute(self):
        if self._fail:
            raise RuntimeError('relation "pending_automations" does not exist')
        if self._update is not None:
            for row in self._rows:
                if self._match(row):
                    row.update(self._update)
            return _Res([])
        return _Res([r for r in self._rows if self._match(r)])


class FakeDB:
    def __init__(self, rows=None, fail=False):
        self.rows = rows or []
        self._fail = fail

    def table(self, name):
        return _Query(self.rows, self._fail)


NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)


def _row(**kw):
    base = {
        "id": "a1",
        "tenant_id": "t1",
        "automation_type": "missed_call_text",
        "payload": {"to": "+15550001"},
        "status": "pending",
        "attempts": 0,
        "scheduled_for": (NOW - timedelta(seconds=5)).isoformat(),  # due
    }
    base.update(kw)
    return base


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_drain_skips_future_scheduled():
    future = _row(scheduled_for=(NOW + timedelta(minutes=5)).isoformat())
    db = FakeDB([future])
    n = rw.drain_pending_automations(db=db, now=NOW, dispatchers={"missed_call_text": lambda t, p: True})
    assert n == 0
    assert future["status"] == "pending"  # untouched


def test_drain_executes_due_items():
    row = _row()
    db = FakeDB([row])
    seen = []
    dispatchers = {"missed_call_text": lambda t, p: seen.append((t, p)) or True}
    n = rw.drain_pending_automations(db=db, now=NOW, dispatchers=dispatchers)
    assert n == 1
    assert row["status"] == "done"
    assert seen == [("t1", {"to": "+15550001"})]  # tenant scope passed through


def test_failure_increments_retry_count():
    row = _row()
    db = FakeDB([row])
    rw.drain_pending_automations(db=db, now=NOW, dispatchers={"missed_call_text": lambda t, p: False})
    assert row["attempts"] == 1
    assert row["status"] == "pending"  # still retryable
    # rescheduled to now + 2min (attempt-2 wait)
    assert row["scheduled_for"] == (NOW + timedelta(seconds=120)).isoformat()


def test_third_failure_marks_failed():
    row = _row(attempts=2)  # two prior failures
    db = FakeDB([row])
    rw.drain_pending_automations(db=db, now=NOW, dispatchers={"missed_call_text": lambda t, p: False})
    assert row["attempts"] == 3
    assert row["status"] == "failed"


def test_exponential_backoff_schedule():
    # attempts 0 -> 1: +2min; 1 -> 2: +10min; 2 -> 3: failed
    for start, expect_wait in ((0, 120), (1, 600)):
        row = _row(attempts=start)
        db = FakeDB([row])
        rw.drain_pending_automations(
            db=db, now=NOW, dispatchers={"missed_call_text": lambda t, p: False}
        )
        assert row["attempts"] == start + 1
        assert row["status"] == "pending"
        assert row["scheduled_for"] == (NOW + timedelta(seconds=expect_wait)).isoformat()


def test_unknown_type_is_treated_as_failure():
    row = _row(automation_type="mystery")
    db = FakeDB([row])
    # empty registry -> no dispatcher -> failure path (retry), not a crash
    n = rw.drain_pending_automations(db=db, now=NOW, dispatchers={})
    assert n == 1
    assert row["attempts"] == 1 and row["status"] == "pending"


def test_drain_fail_open_on_select_error():
    # Table not migrated -> select raises -> drain returns 0, never propagates.
    assert rw.drain_pending_automations(db=FakeDB(fail=True), now=NOW, dispatchers={}) == 0


def test_dispatcher_exception_is_a_failure_not_a_crash():
    row = _row()

    def boom(t, p):
        raise RuntimeError("twilio 500")

    db = FakeDB([row])
    n = rw.drain_pending_automations(db=db, now=NOW, dispatchers={"missed_call_text": boom})
    assert n == 1
    assert row["attempts"] == 1 and row["status"] == "pending"


def test_registry_default_used_when_no_override(monkeypatch):
    row = _row(automation_type="sms_confirm")
    db = FakeDB([row])
    calls = []
    monkeypatch.setitem(rw._DISPATCHERS, "sms_confirm", lambda t, p: calls.append(t) or True)
    rw.drain_pending_automations(db=db, now=NOW)  # no dispatchers= -> uses registry
    assert row["status"] == "done"
    assert calls == ["t1"]
