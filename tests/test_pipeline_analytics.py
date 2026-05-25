"""Unit tests for backend.services.pipeline_analytics.

Pure-function math; no DB dependency. Covers parse_iso edge cases,
compute_pipeline_metrics (won/lost/in-flight/month rollup), and
annotate_days_in_stage (with stage_changed_at, fallback to created_at,
missing dates).
"""

from datetime import datetime, timezone

from backend.services.pipeline_analytics import (
    _parse_iso,
    annotate_days_in_stage,
    compute_pipeline_metrics,
)


WON_STAGE = {"name": "Won", "is_won": True, "is_lost": False}
LOST_STAGE = {"name": "Lost", "is_won": False, "is_lost": True}
QUALIFIED_STAGE = {"name": "Qualified", "is_won": False, "is_lost": False}


class TestParseIso:
    def test_none(self):
        assert _parse_iso(None) is None

    def test_empty_string(self):
        assert _parse_iso("") is None

    def test_invalid_string(self):
        assert _parse_iso("not-a-date") is None

    def test_z_suffix_converted_to_utc(self):
        dt = _parse_iso("2026-01-15T12:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.year == 2026 and dt.month == 1 and dt.day == 15

    def test_naive_datetime_gets_utc(self):
        dt = _parse_iso("2026-01-15T12:00:00")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_with_offset_preserved(self):
        dt = _parse_iso("2026-01-15T12:00:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None


class TestComputePipelineMetrics:
    def _now(self):
        return datetime(2026, 5, 15, tzinfo=timezone.utc)

    def test_empty_leads(self):
        result = compute_pipeline_metrics([], [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["total_pipeline_value"] == 0.0
        assert result["total_won_value"] == 0.0
        assert result["conversion_rate"] == 0.0
        assert result["avg_deal_value"] == 0.0
        assert result["avg_days_to_close"] == 0.0
        assert result["leads_by_stage"] == {}
        assert result["deals_this_month"] == 0
        assert result["won_this_month"] == 0

    def test_pipeline_value_excludes_lost(self):
        leads = [
            {"status": "Qualified", "deal_value": 1000, "created_at": "2026-05-01"},
            {"status": "Lost", "deal_value": 500, "created_at": "2026-05-02"},
            {"status": "Won", "deal_value": 2000, "created_at": "2026-05-03"},
        ]
        result = compute_pipeline_metrics(
            leads, [WON_STAGE, LOST_STAGE, QUALIFIED_STAGE], now=self._now()
        )
        assert result["total_pipeline_value"] == 3000.0
        assert result["total_won_value"] == 2000.0

    def test_conversion_rate(self):
        leads = [
            {"status": "Won", "deal_value": 100, "created_at": "2026-05-01"},
            {"status": "Won", "deal_value": 200, "created_at": "2026-05-02"},
            {"status": "Lost", "deal_value": 50, "created_at": "2026-05-03"},
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["conversion_rate"] == round(2 / 3 * 100, 1)

    def test_avg_deal_value_only_won(self):
        leads = [
            {"status": "Won", "deal_value": 100},
            {"status": "Won", "deal_value": 300},
            {"status": "Qualified", "deal_value": 5000},
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["avg_deal_value"] == 200.0

    def test_avg_days_to_close(self):
        leads = [
            {
                "status": "Won",
                "deal_value": 100,
                "created_at": "2026-05-01T00:00:00Z",
                "stage_changed_at": "2026-05-11T00:00:00Z",
            },
            {
                "status": "Won",
                "deal_value": 200,
                "created_at": "2026-05-01T00:00:00Z",
                "stage_changed_at": "2026-05-05T00:00:00Z",
            },
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["avg_days_to_close"] == 7.0

    def test_negative_days_to_close_skipped(self):
        leads = [
            {
                "status": "Won",
                "deal_value": 100,
                "created_at": "2026-05-11T00:00:00Z",
                "stage_changed_at": "2026-05-01T00:00:00Z",
            },
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["avg_days_to_close"] == 0.0

    def test_leads_by_stage_uses_original_status(self):
        leads = [
            {"status": "Qualified"},
            {"status": "Qualified"},
            {"status": "Won"},
            {"status": None},
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["leads_by_stage"] == {"Qualified": 2, "Won": 1, "unknown": 1}

    def test_deals_and_won_this_month(self):
        leads = [
            {"status": "Won", "deal_value": 100, "stage_changed_at": "2026-05-10T00:00:00Z"},
            {"status": "Won", "deal_value": 200, "created_at": "2026-04-15T00:00:00Z"},
            {"status": "Qualified", "created_at": "2026-05-01T00:00:00Z"},
        ]
        result = compute_pipeline_metrics(leads, [WON_STAGE, LOST_STAGE], now=self._now())
        assert result["deals_this_month"] == 2
        assert result["won_this_month"] == 1

    def test_case_insensitive_status_match(self):
        leads = [{"status": "won", "deal_value": 100}]
        result = compute_pipeline_metrics(leads, [WON_STAGE], now=self._now())
        assert result["total_won_value"] == 100.0


class TestAnnotateDaysInStage:
    def _now(self):
        return datetime(2026, 5, 15, tzinfo=timezone.utc)

    def test_uses_stage_changed_at(self):
        leads = [{"stage_changed_at": "2026-05-10T00:00:00Z", "created_at": "2026-05-01"}]
        annotate_days_in_stage(leads, now=self._now())
        assert leads[0]["days_in_stage"] == 5

    def test_falls_back_to_created_at(self):
        leads = [{"created_at": "2026-05-10T00:00:00Z"}]
        annotate_days_in_stage(leads, now=self._now())
        assert leads[0]["days_in_stage"] == 5

    def test_zero_when_no_dates(self):
        leads = [{}]
        annotate_days_in_stage(leads, now=self._now())
        assert leads[0]["days_in_stage"] == 0

    def test_zero_when_invalid_date(self):
        leads = [{"created_at": "garbage"}]
        annotate_days_in_stage(leads, now=self._now())
        assert leads[0]["days_in_stage"] == 0

    def test_in_place_modifies_all_leads(self):
        leads = [
            {"stage_changed_at": "2026-05-13T00:00:00Z"},
            {"stage_changed_at": "2026-05-14T00:00:00Z"},
        ]
        annotate_days_in_stage(leads, now=self._now())
        assert leads[0]["days_in_stage"] == 2
        assert leads[1]["days_in_stage"] == 1
