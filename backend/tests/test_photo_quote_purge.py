"""Tests for the photo-quote 30-day image retention purge job (#40).

Standalone-runnable: the module under test imports its Supabase client lazily
inside the job body, so importing the module here pulls no heavy app deps.
Every Supabase + Storage interaction is faked, so no DB or network is touched.

Run directly:
    python3 -m pytest backend/tests/test_photo_quote_purge.py -v
"""

import asyncio
from datetime import datetime, timedelta, timezone

from backend.services.automation.scheduled import photo_quote_jobs as pq


# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #
class FakeStorageBucket:
    def __init__(self, fail_paths=None):
        self.removed = []
        self._fail_paths = set(fail_paths or [])

    def remove(self, paths):
        # supabase-py accepts a list of object paths
        for p in paths:
            if p in self._fail_paths:
                raise RuntimeError(f"storage boom: {p}")
            self.removed.append(p)
        return {"data": paths}


class FakeStorage:
    def __init__(self, bucket):
        self._bucket = bucket
        self.requested_bucket = None

    def from_(self, bucket):
        self.requested_bucket = bucket
        return self._bucket


class FakeUpdateChain:
    """Records the update payload and the row it targets."""

    def __init__(self, table, sink):
        self._table = table
        self._sink = sink
        self._payload = None

    def update(self, payload):
        self._payload = payload
        return self

    def eq(self, col, val):
        self._sink.append({"table": self._table, "col": col, "val": val,
                           "payload": self._payload})
        return self

    def execute(self):
        return type("R", (), {"data": []})()


class FakeSelectChain:
    def __init__(self, rows, filters=None):
        self._rows = rows
        self._filters = filters if filters is not None else {}

    def select(self, *a, **k):
        return self

    def lt(self, col, val):
        self._filters["lt"] = (col, val)
        return self

    def is_(self, *a, **k):
        return self

    def not_(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class FakeDB:
    def __init__(self, rows, storage, update_sink, filters):
        self._rows = rows
        self.storage = storage
        self._update_sink = update_sink
        self._filters = filters

    def table(self, name):
        # First call in the job is the SELECT; updates go through .update()
        chain = FakeSelectChain(self._rows, self._filters)
        # Attach update() so the same object serves both read + write shapes
        chain.update = lambda payload: FakeUpdateChain(name, self._update_sink).update(payload)
        return chain


def _install(monkeypatch, rows, *, fail_paths=None, hour=3):
    bucket = FakeStorageBucket(fail_paths=fail_paths)
    storage = FakeStorage(bucket)
    sink = []
    filters = {}
    db = FakeDB(rows, storage, sink, filters)
    _install.filters = filters
    monkeypatch.setattr(pq, "get_service_supabase", lambda: db)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 21, hour, 5, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(pq, "datetime", _FixedDatetime)
    return bucket, storage, sink


def _run():
    return asyncio.new_event_loop().run_until_complete(
        pq.purge_photo_quote_images_30d()
    )


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_hour_gate_noop_outside_0300(monkeypatch):
    """Job only runs in the 03:00 UTC window; other hours are a no-op."""
    _install(monkeypatch, [{"id": "1", "image_url": "x/a.jpg"}], hour=10)
    result = _run()
    assert result["processed"] == 0
    assert result["skipped_reason"] == "outside_window"


def test_empty_batch_returns_zero(monkeypatch):
    _install(monkeypatch, [])
    result = _run()
    assert result == {"processed": 0, "errors": 0, "duration": result["duration"]}


def test_purges_old_row_deletes_storage_and_nulls_db(monkeypatch):
    rows = [{"id": "row-1",
             "image_url": "https://p.supabase.co/storage/v1/object/public/photo-quotes/t1/full.jpg"}]
    bucket, storage, sink = _install(monkeypatch, rows)
    result = _run()

    assert result["processed"] == 1
    assert result["errors"] == 0
    # storage object path extracted relative to the bucket
    assert storage.requested_bucket == "photo-quotes"
    assert bucket.removed == ["t1/full.jpg"]
    # DB row nulled + timestamped
    assert len(sink) == 1
    payload = sink[0]["payload"]
    assert payload["image_url"] is None
    assert "full_image_purged_at" in payload
    assert sink[0]["col"] == "id"
    assert sink[0]["val"] == "row-1"


def test_storage_failure_still_nulls_db_and_counts_error(monkeypatch):
    rows = [{"id": "row-1", "image_url": "photo-quotes/t1/full.jpg"}]
    bucket, storage, sink = _install(
        monkeypatch, rows, fail_paths={"t1/full.jpg"}
    )
    result = _run()

    # storage delete failed but the DB row was still purged (log + continue)
    assert result["processed"] == 1
    assert result["errors"] == 1
    assert len(sink) == 1
    assert sink[0]["payload"]["image_url"] is None


def test_bare_path_image_url_used_as_is(monkeypatch):
    rows = [{"id": "r", "image_url": "t9/only.jpg"}]
    bucket, _s, _sink = _install(monkeypatch, rows)
    _run()
    assert bucket.removed == ["t9/only.jpg"]


def test_error_rate_over_5pct_flags_alarm(monkeypatch):
    # 2 rows, both storage-fail -> 100% error rate -> alarm flag set
    rows = [{"id": "a", "image_url": "photo-quotes/a.jpg"},
            {"id": "b", "image_url": "photo-quotes/b.jpg"}]
    _install(monkeypatch, rows, fail_paths={"a.jpg", "b.jpg"})
    result = _run()
    assert result["errors"] == 2
    assert result["alarm"] is True


def test_row_missing_image_url_skipped(monkeypatch):
    rows = [{"id": "r", "image_url": None}]
    bucket, _s, sink = _install(monkeypatch, rows)
    result = _run()
    # nothing to delete; row is not counted as processed
    assert bucket.removed == []
    assert result["processed"] == 0


def test_cutoff_is_30_days_before_now(monkeypatch):
    """The candidate query filters created_at < now()-30d — proving a 29-day-old
    row (created_at newer than the cutoff) is excluded, and a 31-day-old row is
    included, at the DB layer."""
    _install(monkeypatch, [])
    _run()
    col, cutoff_iso = _install.filters["lt"]
    assert col == "created_at"
    cutoff = datetime.fromisoformat(cutoff_iso)
    now = datetime(2026, 7, 21, 3, 5, 0, tzinfo=timezone.utc)
    # exactly 30 days back from the fixed "now"
    assert (now - cutoff).days == 30
    # a 29-day-old row is newer than the cutoff -> excluded; a 31-day-old row
    # is older than the cutoff -> included.
    twenty_nine = now - timedelta(days=29)
    thirty_one = now - timedelta(days=31)
    assert twenty_nine > cutoff
    assert thirty_one < cutoff
