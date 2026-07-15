"""Turn-budget guard tests — the bounded-LRU session counter.

Regression for subconscious run 94 (digest 2026-07-15): _SESSION_TURN_COUNTS
was a bare dict that gained one entry per widget session and never evicted,
so a long-running Railway worker's memory grew without limit.
"""

import pytest

from backend.services import widget_guard
from backend.services.widget_guard import _MAX_TRACKED_SESSIONS, check_turn_budget


@pytest.fixture(autouse=True)
def _clean_counter():
    widget_guard._SESSION_TURN_COUNTS.clear()
    yield
    widget_guard._SESSION_TURN_COUNTS.clear()


class TestCheckTurnBudget:
    def test_within_budget_allows(self):
        assert check_turn_budget("s1", max_turns=3) is True
        assert check_turn_budget("s1", max_turns=3) is True
        assert check_turn_budget("s1", max_turns=3) is True

    def test_exceeding_budget_blocks(self):
        for _ in range(40):
            assert check_turn_budget("s1") is True
        assert check_turn_budget("s1") is False

    def test_sessions_counted_independently(self):
        for _ in range(3):
            check_turn_budget("busy", max_turns=3)
        assert check_turn_budget("busy", max_turns=3) is False
        assert check_turn_budget("fresh", max_turns=3) is True


class TestBoundedEviction:
    def test_map_never_exceeds_max_tracked_sessions(self):
        for i in range(_MAX_TRACKED_SESSIONS + 500):
            check_turn_budget(f"session-{i}")
        assert len(widget_guard._SESSION_TURN_COUNTS) == _MAX_TRACKED_SESSIONS

    def test_oldest_session_evicted_first(self):
        for i in range(_MAX_TRACKED_SESSIONS + 1):
            check_turn_budget(f"session-{i}")
        assert "session-0" not in widget_guard._SESSION_TURN_COUNTS
        assert f"session-{_MAX_TRACKED_SESSIONS}" in widget_guard._SESSION_TURN_COUNTS

    def test_recently_bumped_session_survives_eviction(self):
        # session-0 gets re-bumped mid-flood, so it is NOT the LRU entry
        # when eviction kicks in — LRU order follows last bump, not insert.
        check_turn_budget("session-0")
        for i in range(1, _MAX_TRACKED_SESSIONS):
            check_turn_budget(f"session-{i}")
        check_turn_budget("session-0")  # bump to most-recent
        check_turn_budget("overflow-1")  # forces one eviction
        assert "session-0" in widget_guard._SESSION_TURN_COUNTS
        assert "session-1" not in widget_guard._SESSION_TURN_COUNTS

    def test_evicted_session_restarts_count(self):
        for _ in range(5):
            check_turn_budget("s-old", max_turns=5)
        for i in range(_MAX_TRACKED_SESSIONS):
            check_turn_budget(f"flood-{i}")
        # s-old was evicted; returning restarts at 1 (documented soft-ceiling
        # tradeoff) instead of continuing at 6.
        assert check_turn_budget("s-old", max_turns=5) is True
