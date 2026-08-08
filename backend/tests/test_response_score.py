"""Nexlify Score — component math, neutral empty states, grading."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.fake_supabase import db

from backend.services.response_score import (
    _grade,
    _pct,
    compute_response_score,
)


def test_empty_tenant_scores_neutral():
    """Brand-new tenants start at 100/A, not 0/F."""
    result = compute_response_score(db({}), "t1")
    assert result["score"] == 100.0
    assert result["grade"] == "A"
    assert set(result["components"]) == {
        "responsiveness",
        "momentum",
        "conversion",
        "reliability",
    }


def test_untouched_pipeline_scores_low():
    """Old leads still 'new', all stale, no appointments -> weighted floor.

    responsiveness 50 (1 of 2 touched), momentum 0 (both stale),
    conversion 0 (0 appointments / 2 leads), reliability 100 (neutral,
    no finished appointments) -> .4*50 + .25*0 + .2*0 + .15*100 = 35.
    """
    fixture = db(
        {
            "leads": [
                {"id": "l1", "status": "new", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
                {"id": "l2", "status": "contacted", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            ],
        }
    )
    result = compute_response_score(fixture, "t1")
    assert result["components"]["responsiveness"] == 50.0
    assert result["components"]["momentum"] == 0.0
    assert result["components"]["conversion"] == 0.0
    assert result["components"]["reliability"] == 100.0
    assert result["score"] == 35.0
    assert result["grade"] == "F"


def test_reliability_counts_only_finished_appointments():
    fixture = db(
        {
            "appointments": [
                {"id": "a1", "status": "completed", "start_time": "2026-08-01"},
                {"id": "a2", "status": "no_show", "start_time": "2026-08-02"},
                {"id": "a3", "status": "confirmed", "start_time": "2026-08-20"},
            ],
        }
    )
    result = compute_response_score(fixture, "t1")
    assert result["components"]["reliability"] == 50.0


def test_grade_bands():
    assert _grade(95) == "A"
    assert _grade(80) == "B"
    assert _grade(65) == "C"
    assert _grade(45) == "D"
    assert _grade(10) == "F"


def test_pct_neutral_on_empty_denominator():
    assert _pct(0, 0) == 100.0
    assert _pct(1, 4) == 25.0
