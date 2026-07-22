"""Tests for photo-quote pilot telemetry (#44).

Faked db, standalone:
    python3 -m pytest backend/tests/test_photo_quote_telemetry.py -v --noconftest
"""

from datetime import datetime, timezone

from backend.services import photo_quote_telemetry as tel


# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #
class FakeChain:
    def __init__(self, rows, sink, fail):
        self._rows = rows
        self._sink = sink
        self._fail = fail
        self._payload = None

    def select(self, *a, **k):
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def eq(self, col, val):
        self._sink.append({"col": col, "val": val, "payload": self._payload})
        return self

    def gte(self, *a, **k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *a, **k):
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError("column tenant_feedback does not exist")
        return type("R", (), {"data": self._rows})()


class FakeDB:
    def __init__(self, rows=None, fail=False):
        self._rows = rows or []
        self.writes = []
        self._fail = fail

    def table(self, name):
        return FakeChain(self._rows, self.writes, self._fail)


NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# record_feedback                                                              #
# --------------------------------------------------------------------------- #
def test_record_feedback_valid_writes():
    db = FakeDB()
    ok = tel.record_feedback("t1", "q1", "too_low", db=db)
    assert ok is True
    assert db.writes[0]["payload"] == {"tenant_feedback": "too_low"}
    # scoped by id + client_id
    cols = {w["col"] for w in db.writes}
    assert {"id", "client_id"} <= cols


def test_record_feedback_rejects_invalid_value():
    db = FakeDB()
    assert tel.record_feedback("t1", "q1", "garbage", db=db) is False
    assert db.writes == []  # never touched the DB


def test_record_feedback_fail_open_on_db_error():
    assert tel.record_feedback("t1", "q1", "correct", db=FakeDB(fail=True)) is False


def test_mark_led_to_appointment_sets_true():
    db = FakeDB()
    assert tel.mark_led_to_appointment("t1", "q1", db=db) is True
    assert db.writes[0]["payload"] == {"led_to_appointment": True}


# --------------------------------------------------------------------------- #
# compute_error_rate                                                           #
# --------------------------------------------------------------------------- #
def test_error_rate_counts_non_correct_over_rated():
    rows = [
        {"tenant_feedback": "correct"},
        {"tenant_feedback": "correct"},
        {"tenant_feedback": "too_low"},
        {"tenant_feedback": "unclear"},
    ]
    out = tel.compute_error_rate("t1", db=FakeDB(rows), now=NOW)
    assert out["rated"] == 4
    assert out["errors"] == 2
    assert out["error_rate"] == 0.5
    assert out["over_threshold"] is True  # 50% > 5%


def test_error_rate_under_threshold_flag_false():
    # 1 error in 100 = 1% < 5%
    rows = [{"tenant_feedback": "correct"}] * 99 + [{"tenant_feedback": "too_high"}]
    out = tel.compute_error_rate("t1", db=FakeDB(rows), now=NOW)
    assert out["errors"] == 1 and out["rated"] == 100
    assert out["error_rate"] == 0.01
    assert out["over_threshold"] is False


def test_error_rate_no_ratings_is_zero_not_error():
    out = tel.compute_error_rate("t1", db=FakeDB([]), now=NOW)
    assert out == {"rated": 0, "errors": 0, "error_rate": 0.0, "over_threshold": False}


def test_error_rate_fail_open():
    out = tel.compute_error_rate("t1", db=FakeDB(fail=True), now=NOW)
    assert out["error_rate"] == 0.0 and out["over_threshold"] is False


# --------------------------------------------------------------------------- #
# compute_conversion_rate                                                      #
# --------------------------------------------------------------------------- #
def test_conversion_rate_counts_led_to_appointment():
    rows = [
        {"led_to_appointment": True},
        {"led_to_appointment": False},
        {"led_to_appointment": True},
        {"led_to_appointment": False},
    ]
    out = tel.compute_conversion_rate("t1", db=FakeDB(rows), now=NOW)
    assert out["total"] == 4 and out["converted"] == 2
    assert out["conversion_rate"] == 0.5


def test_conversion_rate_empty_is_zero():
    out = tel.compute_conversion_rate("t1", db=FakeDB([]), now=NOW)
    assert out == {"total": 0, "converted": 0, "conversion_rate": 0.0}
