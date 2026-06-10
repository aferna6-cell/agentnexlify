"""Tests for the pricing A/B readout aggregation (ops/evals/run_pricing_ab_report.py)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ops.evals.run_pricing_ab_report import build_report


def test_unique_visitors_counted_once():
    rows = [
        {"visitor_id": "a", "variant": "control", "event": "view"},
        {"visitor_id": "a", "variant": "control", "event": "view"},
        {"visitor_id": "b", "variant": "control", "event": "view"},
        {"visitor_id": "a", "variant": "control", "event": "cta_click"},
    ]
    report = build_report(rows)
    assert report["control"]["unique_viewers"] == 2
    assert report["control"]["unique_clickers"] == 1
    assert report["control"]["conversion_pct"] == 50.0


def test_low_sample_flagged():
    rows = [{"visitor_id": f"v{i}", "variant": "variant_b", "event": "view"} for i in range(5)]
    assert build_report(rows)["variant_b"]["sample_warning"] is True


def test_empty_and_malformed_rows_safe():
    assert build_report([]) == {}
    report = build_report([{"visitor_id": None, "variant": "control", "event": "view"}])
    assert report == {}
