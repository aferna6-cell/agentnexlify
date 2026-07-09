"""Tests for SMS opt-out suppression (TCPA). Offline — fake Supabase chains."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("TESTING", "1")

from backend.services import sms_compliance as sc


# --- pure helpers -----------------------------------------------------------

def test_last10_normalizes_formats():
    assert sc.last10("+1 (203) 555-0148") == "2035550148"
    assert sc.last10("203-555-0148") == "2035550148"
    assert sc.last10("") == ""
    assert sc.last10(None) == ""


def test_classify_inbound():
    assert sc.classify_inbound("STOP") == "opt_out"
    assert sc.classify_inbound(" stop ") == "opt_out"
    assert sc.classify_inbound("UNSUBSCRIBE") == "opt_out"
    assert sc.classify_inbound("START") == "opt_in"
    assert sc.classify_inbound("unstop") == "opt_in"
    assert sc.classify_inbound("stop by the shop tomorrow") is None
    assert sc.classify_inbound("hello") is None
    assert sc.classify_inbound("") is None


# --- fake DB ----------------------------------------------------------------

class _Chain:
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def filter(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        r = MagicMock()
        r.data = self._data
        return r


def _db(opt_out_rows=None, leads_rows=None, opt_out_raises=False, mct_rows=None):
    def _table(name):
        if name == "sms_opt_outs":
            return _Chain(data=opt_out_rows, raise_on_execute=opt_out_raises)
        if name == "leads":
            return _Chain(data=leads_rows)
        if name == "missed_call_texts":
            return _Chain(data=mct_rows)
        return _Chain()
    db = MagicMock()
    db.table.side_effect = _table
    return db


def test_recently_messaged_true_when_recent_row():
    db = _db(mct_rows=[{"id": "x"}])
    assert sc.recently_messaged(db, "t1", "+12035550148") is True


def test_recently_messaged_false_when_none():
    db = _db(mct_rows=[])
    assert sc.recently_messaged(db, "t1", "+12035550148") is False


def test_recently_messaged_blank_phone_false():
    assert sc.recently_messaged(_db(), "t1", "") is False


# --- is_suppressed ----------------------------------------------------------

def test_suppressed_when_in_optout_table():
    db = _db(opt_out_rows=[{"id": "x"}])
    assert sc.is_suppressed(db, "t1", "+12035550148") is True


def test_suppressed_via_leads_unsubscribed():
    db = _db(opt_out_rows=[], leads_rows=[{"phone": "(203) 555-0148", "unsubscribed": True}])
    assert sc.is_suppressed(db, "t1", "+1 203 555 0148") is True


def test_not_suppressed_when_clean():
    db = _db(opt_out_rows=[], leads_rows=[{"phone": "2229991111", "unsubscribed": True}])
    assert sc.is_suppressed(db, "t1", "+12035550148") is False


def test_blank_phone_not_suppressed():
    assert sc.is_suppressed(_db(), "t1", "") is False


def test_optout_lookup_error_fails_closed():
    # A lookup failure must SUPPRESS the send (legal-safe), not allow it.
    db = _db(opt_out_raises=True)
    assert sc.is_suppressed(db, "t1", "+12035550148") is True


# --- record_opt_out / record_opt_in ----------------------------------------

class _StatefulDB:
    """In-memory sms_opt_outs so we can assert observable suppression state
    after record_opt_out / record_opt_in (behavioral, not interaction-only)."""

    def __init__(self):
        self.store: set[tuple[str, str]] = set()  # (client_id, phone_last10)

    def table(self, name):
        return _StatefulChain(self, name)


class _StatefulChain:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self._eqs: dict[str, str] = {}
        self._op = None
        self._row = None

    def select(self, *a, **k): self._op = "select"; return self
    def delete(self, *a, **k): self._op = "delete"; return self
    def limit(self, *a, **k): return self
    def filter(self, *a, **k): return self

    def upsert(self, row, **k):
        self._op = "upsert"; self._row = row; return self

    def eq(self, col, val):
        self._eqs[col] = val
        return self

    def execute(self):
        r = MagicMock()
        if self.name != "sms_opt_outs":
            r.data = []
            return r
        if self._op == "upsert":
            self.db.store.add((self._row["client_id"], self._row["phone_last10"]))
            r.data = [self._row]
        elif self._op == "delete":
            key = (self._eqs.get("client_id"), self._eqs.get("phone_last10"))
            self.db.store.discard(key)
            r.data = []
        else:  # select
            key = (self._eqs.get("client_id"), self._eqs.get("phone_last10"))
            r.data = [{"id": "x"}] if key in self.db.store else []
        return r


def test_opt_out_then_suppressed_roundtrip():
    db = _StatefulDB()
    phone = "+1 (203) 555-0148"
    assert sc.is_suppressed(db, "t1", phone) is False
    sc.record_opt_out(db, "t1", phone)
    # Observable: the recipient is now suppressed (any phone format matches).
    assert sc.is_suppressed(db, "t1", "2035550148") is True
    # And re-subscribing clears it.
    sc.record_opt_in(db, "t1", "+12035550148")
    assert sc.is_suppressed(db, "t1", phone) is False


def test_record_opt_out_blank_phone_is_noop():
    db = _StatefulDB()
    sc.record_opt_out(db, "t1", "")  # blank phone records nothing
    assert db.store == set()
    assert sc.is_suppressed(db, "t1", "+12035550148") is False
