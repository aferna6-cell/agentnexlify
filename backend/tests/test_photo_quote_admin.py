"""Tests for the Quote Requests dashboard read-side (#42).

Faked db, standalone:
    python3 -m pytest backend/tests/test_photo_quote_admin.py -v --noconftest
"""

from datetime import datetime, timezone

from backend.services import photo_quote_admin_service as adm
from backend.services import photo_quote_usage as usage


# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #
class FakeQuery:
    def __init__(self, rows, calls):
        self._rows = rows
        self._calls = calls

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._calls.setdefault("eq", []).append((col, val))
        return self

    def gte(self, col, val):
        self._calls["gte"] = (col, val)
        return self

    def lte(self, col, val):
        self._calls["lte"] = (col, val)
        return self

    def order(self, col, desc=False):
        self._calls["order"] = (col, desc)
        return self

    def limit(self, n):
        self._calls["limit"] = n
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.calls = {}

    def table(self, name):
        return FakeQuery(self._rows, self.calls)


ROW = {
    "id": "q1", "conversation_id": "c1", "image_url": "t/full.bin",
    "thumbnail_url": "t/thumb.jpg", "full_image_purged_at": None,
    "quote_low": 150, "quote_high": 400, "severity": "minor",
    "confidence": 0.9, "claude_summary": "leak", "needs_human": False,
    "created_at": "2026-07-20T10:00:00+00:00",
}


# --------------------------------------------------------------------------- #
# list_quote_requests                                                          #
# --------------------------------------------------------------------------- #
def test_list_shapes_rows_and_orders_newest_first():
    db = FakeDB([ROW])
    out = adm.list_quote_requests("t1", db=db)
    assert len(out) == 1
    assert out[0]["id"] == "q1"
    assert out[0]["summary"] == "leak"
    assert out[0]["image_purged"] is False
    # newest-first ordering requested
    assert db.calls["order"] == ("created_at", True)
    # tenant-scoped by client_id
    assert ("client_id", "t1") in db.calls["eq"]


def test_list_marks_purged_image():
    purged = dict(ROW, full_image_purged_at="2026-06-01T00:00:00+00:00", image_url=None)
    out = adm.list_quote_requests("t1", db=FakeDB([purged]))
    assert out[0]["image_purged"] is True


def test_list_needs_human_filter_applied():
    db = FakeDB([ROW])
    adm.list_quote_requests("t1", db=db, needs_human=True)
    assert ("needs_human", True) in db.calls["eq"]


def test_list_date_range_applied():
    db = FakeDB([ROW])
    adm.list_quote_requests("t1", db=db, start_date="2026-07-01", end_date="2026-07-31")
    assert db.calls["gte"] == ("created_at", "2026-07-01")
    assert db.calls["lte"] == ("created_at", "2026-07-31")


def test_list_caps_limit():
    db = FakeDB([ROW])
    adm.list_quote_requests("t1", db=db, limit=99999)
    assert db.calls["limit"] == 500  # capped at _MAX_LIMIT


def test_list_fail_open_returns_empty():
    class Boom:
        def table(self, *a, **k):
            raise RuntimeError("db down")
    assert adm.list_quote_requests("t1", db=Boom()) == []


# --------------------------------------------------------------------------- #
# get_usage_summary                                                            #
# --------------------------------------------------------------------------- #
class UsageDB:
    def __init__(self, row):
        self._row = row

    def table(self, name):
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": [self._row] if self._row else []})()


NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


def test_usage_summary_computes_overage_charge():
    db = UsageDB({"quote_count": 512, "overage_count": 12})
    s = usage.get_usage_summary("t1", db=db, now=NOW)
    assert s["quote_count"] == 512
    assert s["overage_count"] == 12
    assert s["cap"] == 500
    assert s["overage_charge"] == round(12 * 0.15, 2)  # 1.80


def test_usage_summary_zero_when_no_row():
    s = usage.get_usage_summary("t1", db=UsageDB(None), now=NOW)
    assert s == {"quote_count": 0, "overage_count": 0, "cap": 500, "overage_charge": 0.0}
