"""Tests for the booking↔GCal companion module (#119 core).

Injectable deps (db, create_event, now) so this runs standalone with no app
boot and no network:
    python3 -m pytest backend/tests/test_booking_gcal.py -v --noconftest
"""

from datetime import datetime, timezone

from backend.services import booking_gcal as bg


# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #
class FakeChain:
    def __init__(self, sink, table):
        self._sink = sink
        self._table = table
        self._payload = None

    def update(self, payload):
        self._payload = payload
        return self

    def insert(self, payload):
        self._sink.append({"op": "insert", "table": self._table, "payload": payload})
        return self

    def eq(self, col, val):
        self._sink.append(
            {"op": "update", "table": self._table, "col": col, "val": val,
             "payload": self._payload}
        )
        return self

    def execute(self):
        return type("R", (), {"data": []})()


class FakeDB:
    def __init__(self, *, insert_fail_tables=None):
        self.ops = []
        self._insert_fail = set(insert_fail_tables or [])

    def table(self, name):
        if name in self._insert_fail:
            db = self

            class Boom:
                def update(self, *a, **k): return self
                def insert(self, *a, **k): return self
                def eq(self, *a, **k): return self
                def execute(self): raise RuntimeError("table missing")
            return Boom()
        return FakeChain(self.ops, name)


NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# create_gcal_event                                                            #
# --------------------------------------------------------------------------- #
def test_create_gcal_event_success_writes_back_event_id():
    db = FakeDB()
    calls = []

    def fake_create(tenant_id, summary, start, end, attendee_email=None, description=None):
        calls.append((tenant_id, summary, start, end, attendee_email))
        return "evt_123"

    appt = {"id": "a1", "start_utc": "2026-07-22T15:00:00+00:00",
            "end_utc": "2026-07-22T16:00:00+00:00", "customer_email": "x@y.com",
            "service": "Inspection"}
    result = bg.create_gcal_event("t1", appt, db=db, create_event=fake_create)

    assert result == "evt_123"
    assert calls and calls[0][0] == "t1"
    # gcal_event_id written back to the appointments row by id
    ups = [o for o in db.ops if o["op"] == "update" and o["table"] == "appointments"]
    assert ups and ups[0]["payload"]["gcal_event_id"] == "evt_123"
    assert ups[0]["col"] == "id" and ups[0]["val"] == "a1"


def test_create_gcal_event_returns_none_when_gcal_declines():
    db = FakeDB()
    result = bg.create_gcal_event(
        "t1", {"id": "a1", "start_utc": "2026-07-22T15:00:00+00:00",
               "end_utc": "2026-07-22T16:00:00+00:00"},
        db=db, create_event=lambda *a, **k: None,
    )
    assert result is None
    # no write-back when there is no event id
    assert not [o for o in db.ops if o["op"] == "update"]


def test_create_gcal_event_writeback_failure_is_swallowed():
    db = FakeDB(insert_fail_tables={"appointments"})
    # gcal succeeds, DB write-back raises -> still returns the event id, never raises
    result = bg.create_gcal_event(
        "t1", {"id": "a1", "start_utc": "2026-07-22T15:00:00+00:00",
               "end_utc": "2026-07-22T16:00:00+00:00"},
        db=db, create_event=lambda *a, **k: "evt_9",
    )
    assert result == "evt_9"


# --------------------------------------------------------------------------- #
# handle_gcal_failure                                                          #
# --------------------------------------------------------------------------- #
def test_handle_gcal_failure_sets_pending_sync_and_enqueues():
    db = FakeDB()
    bg.handle_gcal_failure("t1", "a1", db=db, now=NOW)

    updates = [o for o in db.ops if o["op"] == "update" and o["table"] == "appointments"]
    assert updates and updates[0]["payload"]["status"] == "pending_sync"
    assert updates[0]["val"] == "a1"

    inserts = [o for o in db.ops if o["op"] == "insert" and o["table"] == "pending_automations"]
    assert inserts, "should enqueue a pending_automations retry row"
    payload = inserts[0]["payload"]
    assert payload["automation_type"] == "appointment_sync"
    assert payload["tenant_id"] == "t1"


def test_handle_gcal_failure_swallows_missing_pending_table():
    # pending_automations not applied yet (migration 180) -> must not raise
    db = FakeDB(insert_fail_tables={"pending_automations"})
    bg.handle_gcal_failure("t1", "a1", db=db, now=NOW)  # no exception
    # the status update to appointments still went through
    assert [o for o in db.ops if o["table"] == "appointments"]


# --------------------------------------------------------------------------- #
# rule_based_slots  (GCal-OAuth-expiry fallback — no API spend)                #
# --------------------------------------------------------------------------- #
def test_rule_based_slots_returns_five_future_hourly_windows():
    slots = bg.rule_based_slots(now=NOW, booked_starts=set(), count=5)
    assert len(slots) == 5
    for s in slots:
        assert "start" in s and "end" in s and "display" in s
        start = datetime.fromisoformat(s["start"])
        assert start > NOW  # only future
        # within 09:00–17:00 window, 60-min slots
        assert 9 <= start.hour <= 16


def test_rule_based_slots_skips_booked_starts():
    # book the first candidate the generator would produce
    first = bg.rule_based_slots(now=NOW, booked_starts=set(), count=1)[0]["start"]
    slots = bg.rule_based_slots(now=NOW, booked_starts={first}, count=3)
    assert first not in {s["start"] for s in slots}


# --------------------------------------------------------------------------- #
# next_available_alternates  (409 race response)                              #
# --------------------------------------------------------------------------- #
def test_next_available_alternates_excludes_taken_slot_returns_three():
    available = bg.rule_based_slots(now=NOW, booked_starts=set(), count=6)
    taken = available[0]["start"]
    alts = bg.next_available_alternates(available, taken_start=taken, count=3)
    assert len(alts) == 3
    assert taken not in {a["start"] for a in alts}


def test_next_available_alternates_caps_at_available():
    available = bg.rule_based_slots(now=NOW, booked_starts=set(), count=2)
    alts = bg.next_available_alternates(available, taken_start=available[0]["start"], count=3)
    # only 1 remains after removing the taken slot
    assert len(alts) == 1
