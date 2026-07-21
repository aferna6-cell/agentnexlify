"""Tests for missed-call text-back gating + retry enqueue (#117).

Pure/injectable — runs standalone:
    python3 -m pytest backend/tests/test_missed_call_gate.py -v --noconftest
"""

from datetime import datetime, timezone

from backend.services import missed_call_gate as g
from backend.services.plan_catalog import PREMIUM_PLANS

NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# plan gate                                                                    #
# --------------------------------------------------------------------------- #
def test_premium_plans_are_eligible():
    for plan in PREMIUM_PLANS:
        assert g.is_plan_eligible(plan)
    # agent_os is the current premium tier and must be eligible
    assert g.is_plan_eligible("agent_os")


def test_free_and_chatbot_and_none_are_not_eligible():
    assert not g.is_plan_eligible("free")
    assert not g.is_plan_eligible("chatbot")  # entry tier, no branded automation
    assert not g.is_plan_eligible(None)
    assert not g.is_plan_eligible("")


# --------------------------------------------------------------------------- #
# spam blocklist                                                               #
# --------------------------------------------------------------------------- #
def test_spam_blocklist_matches_regardless_of_formatting():
    config = {"spam_blocklist": ["+1 (555) 123-4567", "5559999999"]}
    assert g.is_spam_blocked("+15551234567", config)
    assert g.is_spam_blocked("555-999-9999", config)


def test_spam_blocklist_absent_or_empty_blocks_nothing():
    assert not g.is_spam_blocked("+15551234567", None)
    assert not g.is_spam_blocked("+15551234567", {})
    assert not g.is_spam_blocked("+15551234567", {"spam_blocklist": []})


def test_spam_blocklist_non_member_passes():
    config = {"spam_blocklist": ["5559999999"]}
    assert not g.is_spam_blocked("+15551234567", config)


# --------------------------------------------------------------------------- #
# duration gate                                                                #
# --------------------------------------------------------------------------- #
def test_duration_over_ten_seconds_skips():
    assert g.should_skip_for_duration("30")
    assert g.should_skip_for_duration(45)


def test_duration_ten_or_less_does_not_skip():
    assert not g.should_skip_for_duration("10")
    assert not g.should_skip_for_duration("0")
    assert not g.should_skip_for_duration(5)


def test_duration_missing_or_garbage_does_not_skip():
    assert not g.should_skip_for_duration("")
    assert not g.should_skip_for_duration(None)
    assert not g.should_skip_for_duration("abc")


# --------------------------------------------------------------------------- #
# retry enqueue (fail-open)                                                     #
# --------------------------------------------------------------------------- #
class FakeChain:
    def __init__(self, sink, fail):
        self._sink = sink
        self._fail = fail

    def insert(self, payload):
        if self._fail:
            raise RuntimeError("relation pending_automations does not exist")
        self._sink.append(payload)
        return self

    def execute(self):
        return type("R", (), {"data": []})()


class FakeDB:
    def __init__(self, fail=False):
        self.rows = []
        self._fail = fail

    def table(self, name):
        return FakeChain(self.rows, self._fail)


def test_enqueue_writes_pending_automations_row():
    db = FakeDB()
    ok = g.enqueue_missed_call_retry(
        "t1", {"caller": "+15551234567", "call_sid": "CA1"}, db=db, now=NOW
    )
    assert ok is True
    assert len(db.rows) == 1
    row = db.rows[0]
    assert row["tenant_id"] == "t1"
    assert row["automation_type"] == "missed_call_text"
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["payload"]["caller"] == "+15551234567"


def test_enqueue_is_fail_open_when_table_missing():
    db = FakeDB(fail=True)
    ok = g.enqueue_missed_call_retry("t1", {"caller": "x"}, db=db, now=NOW)
    assert ok is False  # swallowed, never raised
