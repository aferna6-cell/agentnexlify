"""Unit tests for backend/services/analytics_common.py.

The module moved from backend/routers/analytics/_common.py (audit 2026-07-14
M2 layer-inversion fix). Router flow tests exercise most of it indirectly;
these cover the pure helpers directly, including the branches the flow tests
never hit (cache expiry/eviction, parse failures, empty-input fallbacks).
"""

import time

import pytest

from backend.services import analytics_common as ac


@pytest.fixture(autouse=True)
def _clean_cache():
    ac._cache.clear()
    yield
    ac._cache.clear()


class TestCache:
    def test_set_then_get_roundtrips(self):
        ac._set_cache("k", {"v": 1})
        assert ac._get_cached("k") == {"v": 1}

    def test_missing_key_returns_none(self):
        assert ac._get_cached("nope") is None

    def test_expired_entry_evicted_on_read(self):
        ac._cache["old"] = (time.time() - ac._CACHE_TTL - 1, {"v": 1})
        assert ac._get_cached("old") is None
        assert "old" not in ac._cache

    def test_set_evicts_expired_when_cache_large(self):
        stale_ts = time.time() - ac._CACHE_TTL - 1
        for i in range(501):
            ac._cache[f"stale-{i}"] = (stale_ts, {})
        ac._set_cache("fresh", {"v": 2})
        assert ac._get_cached("fresh") == {"v": 2}
        assert not any(k.startswith("stale-") for k in ac._cache)


class TestScalarHelpers:
    def test_pct_change_zero_previous(self):
        assert ac._pct_change(5, 0) == 100.0
        assert ac._pct_change(0, 0) == 0.0

    def test_pct_change_normal(self):
        assert ac._pct_change(150, 100) == 50.0

    def test_parse_dt_handles_z_suffix_and_garbage(self):
        assert ac._parse_dt("2026-07-15T10:00:00Z") is not None
        assert ac._parse_dt("not-a-date") is None
        assert ac._parse_dt(None) is None

    def test_safe_float(self):
        assert ac._safe_float("3.5") == 3.5
        assert ac._safe_float(None) == 0.0
        assert ac._safe_float("garbage") == 0.0

    def test_ratio(self):
        assert ac._ratio(1, 4) == 25.0
        assert ac._ratio(1, 0) == 0.0

    def test_clamp_and_status(self):
        assert ac._clamp_score(150) == 100
        assert ac._clamp_score(-5) == 0
        assert ac._score_status(85) == "strong"
        assert ac._score_status(65) == "watch"
        assert ac._score_status(10) == "at_risk"

    def test_period_to_days(self):
        assert ac._period_to_days("7d") == 7
        assert ac._period_to_days("bogus") == 30

    def test_date_range_shapes(self):
        start, prev_start = ac._date_range(7)
        assert start > prev_start  # ISO strings compare chronologically


class TestConversationHelpers:
    def test_first_response_seconds(self):
        msgs = [
            {"role": "user", "created_at": "2026-07-15T10:00:00+00:00"},
            {"role": "assistant", "created_at": "2026-07-15T10:00:30+00:00"},
        ]
        assert ac._first_response_seconds(msgs) == 30.0

    def test_first_response_none_without_assistant_reply(self):
        msgs = [{"role": "user", "created_at": "2026-07-15T10:00:00+00:00"}]
        assert ac._first_response_seconds(msgs) is None

    def test_first_response_skips_unparseable_timestamps(self):
        msgs = [
            {"role": "user", "created_at": "garbage"},
            {"role": "user", "created_at": "2026-07-15T10:00:00+00:00"},
            {"role": "assistant", "created_at": "2026-07-15T10:00:10+00:00"},
        ]
        assert ac._first_response_seconds(msgs) == 10.0

    def test_preview_text_truncates_with_ellipsis(self):
        assert ac._preview_text("  short  ") == "short"
        long = "x" * 200
        out = ac._preview_text(long, limit=50)
        assert len(out) == 50 and out.endswith("...")
        assert ac._preview_text(None) == ""


class TestRecommendations:
    def test_healthy_fallback_when_nothing_flagged(self):
        recs = ac._build_control_center_recommendations(
            total_conversations=0,
            assisted_conversations=0,
            lead_count=0,
            booked_count=0,
            recovery_queue=[],
            pricing_gap_count=0,
            no_response_count=0,
            at_risk_pipeline_value=0.0,
        )
        assert len(recs) == 1
        assert "healthy" in recs[0]

    def test_all_signals_capped_at_four(self):
        recs = ac._build_control_center_recommendations(
            total_conversations=10,
            assisted_conversations=5,
            lead_count=8,
            booked_count=2,
            recovery_queue=[{"id": 1}],
            pricing_gap_count=3,
            no_response_count=2,
            at_risk_pipeline_value=1200.0,
        )
        assert len(recs) == 4
        assert any("recovery" in r for r in recs)
