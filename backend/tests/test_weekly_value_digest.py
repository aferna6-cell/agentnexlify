"""Tests for the weekly value digest (gap G2). Spec: specs/weekly-value-digest_spec.md.

Covers the pure rollup (happy / zero-activity / new-tenant / missing-value), the HTML body,
and the safety gates: no send without opt-in, idempotency, draft-by-default.
"""

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.automation.weekly_value_digest import (  # noqa: E402
    build_digest_html,
    run_weekly_digests,
    summarize_week,
    week_bounds,
)


# --- pure rollup ------------------------------------------------------------

def test_week_bounds_is_prior_complete_monday_week():
    # Wed 2026-06-17 → last complete week is Mon 2026-06-08 .. Mon 2026-06-15.
    start, end = week_bounds(date(2026, 6, 17))
    assert start == date(2026, 6, 8)
    assert end == date(2026, 6, 15)


def test_summarize_happy_path_with_delta_and_invoiced_value():
    s = summarize_week(
        {"leads": 12, "conversations": 40, "appointments": 5, "after_hours": 3, "invoiced_cents": 250000},
        previous={"leads": 8},
    )
    assert s["leads"] == 12
    assert s["leads_delta"] == 4
    assert s["estimated_value_cents"] == 250000
    assert s["estimated_value_display"] == "$2,500"
    assert s["value_basis"] == "invoiced"
    assert s["has_activity"] is True


def test_summarize_estimates_from_avg_when_no_invoices():
    s = summarize_week({"leads": 10}, avg_job_value_cents=20000)
    assert s["estimated_value_cents"] == 200000
    assert s["value_basis"] == "estimated"


def test_summarize_never_fabricates_value():
    s = summarize_week({"leads": 5})  # no invoices, no avg value
    assert s["estimated_value_cents"] is None
    assert s["estimated_value_display"] is None
    assert s["value_basis"] == "none"


def test_summarize_zero_activity_flag():
    s = summarize_week({"leads": 0, "conversations": 0, "appointments": 0})
    assert s["has_activity"] is False


# --- html body --------------------------------------------------------------

def test_html_contains_numbers_and_unsubscribe():
    s = summarize_week({"leads": 3, "conversations": 9, "appointments": 1, "after_hours": 0})
    html = build_digest_html(s, "Sunset Auto Care", "https://app.example/unsub?t=1")
    assert "Sunset Auto Care" in html
    assert "New leads captured" in html
    assert "Unsubscribe" in html
    assert "https://app.example/unsub?t=1" in html


def test_html_omits_dollar_line_when_no_value():
    s = summarize_week({"leads": 2, "conversations": 1, "appointments": 0})
    html = build_digest_html(s, "Biz", "https://x/u")
    assert "Estimated value" not in html


# --- safety gates (fake db) -------------------------------------------------

class _Result:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class _Query:
    """Minimal chainable Supabase-query stand-in driven by a fixed result."""

    def __init__(self, result):
        self._result = result

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def lt(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, *a, **k):
        return self

    def execute(self):
        return self._result


class _FakeDB:
    def __init__(self, tenants):
        self._tenants = tenants
        self.inserted = []

    def table(self, name):
        if name == "tenants":
            return _Query(_Result(data=self._tenants))
        if name == "digest_sends":
            db = self

            class _Ledger(_Query):
                def insert(self, row, *a, **k):
                    db.inserted.append(row)
                    return self

            return _Ledger(_Result(data=[]))  # never previously sent
        # leads/conversations/appointments counts
        return _Query(_Result(count=4))


def test_run_is_draft_by_default_no_send():
    db = _FakeDB([{"id": "t1", "client_id": "c1", "business_name": "Biz", "created_at": "2026-01-01"}])
    drafts = run_weekly_digests(db, send=False, today=date(2026, 6, 17))
    assert len(drafts) == 1
    assert drafts[0].get("sent") is None
    assert db.inserted == []  # nothing recorded → nothing sent


def test_run_skips_tenant_younger_than_a_week():
    # created 2 days before the digest week start → skipped
    db = _FakeDB([{"id": "t1", "client_id": "c1", "business_name": "Biz", "created_at": "2026-06-07"}])
    drafts = run_weekly_digests(db, send=True, today=date(2026, 6, 17))
    assert drafts == []
    assert db.inserted == []


def test_run_records_idempotency_row_only_when_sending():
    db = _FakeDB([{"id": "t1", "client_id": "c1", "business_name": "Biz", "created_at": "2026-01-01"}])
    drafts = run_weekly_digests(db, send=True, today=date(2026, 6, 17))
    assert drafts and drafts[0].get("sent") is True
    assert len(db.inserted) == 1
    assert db.inserted[0]["tenant_id"] == "t1"
