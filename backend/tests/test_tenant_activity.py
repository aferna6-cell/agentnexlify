"""Shared activity counters used by dashboard, billing, and analytics."""

from datetime import datetime, timezone

from backend.services.tenant_activity import (
    activity_window,
    count_conversations,
    count_leads_created,
    in_window,
    last_activity_at,
    session_timestamps,
)


NOW = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)


def _conv(session_id, started_at, last_message_at=None):
    return {
        "session_id": session_id,
        "started_at": started_at,
        "last_message_at": last_message_at,
    }


def _msg(session_id, created_at):
    return {"session_id": session_id, "created_at": created_at}


class TestConversationCount:
    def test_session_on_conversations_counts_inside_month(self):
        """A conversations row this month counts even when chat messages are older."""
        conversations = [_conv("s1", "2026-11-02T12:00:00Z", "2026-11-02T12:05:00Z")]
        messages = [_msg("s1", "2026-08-28T12:00:00Z")]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations(conversations, messages, start, end) == 1

    def test_message_only_session_counts(self):
        messages = [_msg("s-only", "2026-11-01T00:00:00Z")]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations([], messages, start, end) == 1

    def test_same_session_in_both_tables_counts_once(self):
        conversations = [_conv("s1", "2026-11-03T00:00:00Z")]
        messages = [
            _msg("s1", "2026-11-03T00:01:00Z"),
            _msg("s1", "2026-11-03T00:02:00Z"),
        ]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations(conversations, messages, start, end) == 1

    def test_old_message_is_outside_the_month(self):
        messages = [_msg("old", "2026-08-28T12:00:00Z")]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations([], messages, start, end) == 0

    def test_session_without_session_id_uses_row_id(self):
        rows = [{"id": "conv-1", "started_at": "2026-11-03T00:00:00Z"}]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations(rows, [], start, end) == 1

    def test_empty_inputs(self):
        assert count_conversations([], [], *activity_window("month", NOW)[:2]) == 0

    def test_null_and_garbage_timestamps_are_ignored(self):
        rows = [
            {"session_id": "blank", "started_at": None, "last_message_at": ""},
            {"session_id": "bad", "started_at": "not-a-date"},
        ]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations(rows, [{"session_id": None, "created_at": "nope"}], start, end) == 0

    def test_window_is_half_open(self):
        start, end, _prev = activity_window("month", NOW)
        assert in_window(start, start, end) is True
        assert in_window(end, start, end) is False

    def test_large_session_set_counts_each_once(self):
        messages = [
            _msg(f"s{i}", "2026-11-02T00:00:00Z") for i in range(5000)
        ]
        start, end, _prev = activity_window("month", NOW)
        assert count_conversations([], messages, start, end) == 5000


class TestLeadsAndLastActivity:
    def test_all_time_lead_stock_ignores_the_month_window(self):
        leads = [
            {"id": "a", "created_at": "2026-08-01T00:00:00Z"},
            {"id": "b", "created_at": "2026-11-03T00:00:00Z"},
        ]
        assert count_leads_created(leads, None, None) == 2

    def test_period_lead_count_uses_created_at(self):
        leads = [
            {"id": "a", "created_at": "2026-08-01T00:00:00Z"},
            {"id": "b", "created_at": "2026-11-03T00:00:00Z"},
        ]
        start, end, _prev = activity_window("month", NOW)
        assert count_leads_created(leads, start, end) == 1

    def test_last_activity_prefers_newer_lead_over_old_message(self):
        messages = [_msg("s1", "2026-08-28T12:00:00Z")]
        leads = [{"id": "a", "created_at": "2026-11-01T00:00:00Z", "updated_at": "2026-11-03T08:00:00Z"}]
        last = last_activity_at([], messages, leads)
        assert last is not None
        assert last.day == 3 and last.month == 11

    def test_last_activity_none_when_nothing_parses(self):
        assert last_activity_at([], [], []) is None
        assert last_activity_at([{"session_id": "s"}], [{"created_at": "nope"}], [{"created_at": None}]) is None

    def test_month_window_starts_on_the_first(self):
        start, end, prev = activity_window("month", NOW)
        assert start == datetime(2026, 11, 1, tzinfo=timezone.utc)
        assert end == NOW
        assert prev == datetime(2026, 10, 1, tzinfo=timezone.utc)

    def test_rolling_window_length(self):
        start, end, prev = activity_window("30d", NOW)
        assert (end - start).days == 30
        assert (start - prev).days == 30


class TestSessionMerge:
    def test_timestamps_from_both_sources_are_kept(self):
        sessions = session_timestamps(
            [_conv("s1", "2026-11-01T00:00:00Z")],
            [_msg("s1", "2026-11-02T00:00:00Z")],
        )
        assert len(sessions["s1"]) == 2
