"""Tests for destructive-change audit + recovery (council #7).

Offline — fake Supabase chain. Proves a deleted record's snapshot round-trips
through activity_log.metadata so a merge can be recovered.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("TESTING", "1")

from backend.services import record_audit as ra


def test_destructive_snapshot_captures_full_row():
    row = {"id": "L1", "client_id": "t1", "name": "Jane", "email": "j@x.com", "phone": "203"}
    meta = ra.destructive_snapshot("leads", row, action="lead_merged", related_id="L2")
    snap = ra.extract_snapshot(meta)
    assert snap is not None
    assert snap["table"] == "leads"
    assert snap["action"] == "lead_merged"
    assert snap["deleted_id"] == "L1"
    assert snap["related_id"] == "L2"
    assert snap["row"]["name"] == "Jane"
    # snapshot is a copy — mutating the source row does not change it
    row["name"] = "changed"
    assert snap["row"]["name"] == "Jane"


def test_extract_snapshot_handles_garbage():
    assert ra.extract_snapshot(None) is None
    assert ra.extract_snapshot({}) is None
    assert ra.extract_snapshot({"destructive_snapshot": "nope"}) is None


class _Chain:
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        r = MagicMock()
        r.data = self._data
        return r


def _db(activity_rows):
    db = MagicMock()
    db.table.side_effect = lambda name: _Chain(activity_rows if name == "activity_log" else [])
    return db


def test_find_deleted_snapshot_round_trip():
    row = {"id": "L2", "client_id": "t1", "name": "Dup"}
    meta = ra.destructive_snapshot("leads", row, action="lead_merged", related_id="L1")
    db = _db([
        {"metadata": {"other": 1}, "created_at": "2026-06-26T00:00:00Z"},
        {"metadata": meta, "created_at": "2026-06-26T00:01:00Z"},
    ])
    found = ra.find_deleted_snapshot(db, "t1", "L2")
    assert found is not None
    assert found["row"]["name"] == "Dup"


def test_find_deleted_snapshot_missing_returns_none():
    db = _db([{"metadata": {}, "created_at": "x"}])
    assert ra.find_deleted_snapshot(db, "t1", "L9") is None
    assert ra.find_deleted_snapshot(db, "t1", "") is None


def test_find_deleted_snapshot_fails_soft_on_db_error():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    assert ra.find_deleted_snapshot(db, "t1", "L2") is None
