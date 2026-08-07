"""Daily focus picks — priority order, cap, and empty-state behavior.

Uses the shared fake-supabase helpers: filters are recorded, not applied,
so fixtures are shaped per-table to represent the post-filter result set.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.fake_supabase import db

from backend.services.daily_focus import MAX_PICKS, compute_daily_focus


def test_empty_tenant_yields_no_picks():
    assert compute_daily_focus(db({}), "t1") == []


def test_priority_order_and_cap():
    fixture = db(
        {
            "leads": [
                {"id": "l1", "name": "Amy", "status": "new", "created_at": "2026-08-01"},
                {"id": "l2", "name": "Bob", "status": "new", "created_at": "2026-08-02"},
            ],
            "appointments": [
                {"id": "a1", "customer_name": "Cara", "start_time": "2026-08-06T15:00:00Z"},
            ],
            "invoices": [
                {"id": "i1", "invoice_number": "INV-1", "total": 250, "due_date": "2026-07-01"},
            ],
        }
    )
    picks = compute_daily_focus(fixture, "t1")

    assert len(picks) == MAX_PICKS  # 4 rules fired, capped at 3
    kinds = [p["kind"] for p in picks]
    # New leads are the most time-sensitive and always lead; appointments
    # outrank cold leads and invoices.
    assert kinds[0] == "new_leads"
    assert kinds[1] == "appointments_today"
    for p in picks:
        assert p["title"]
        assert p["reason"]
        assert p["count"] >= 1


def test_new_lead_pick_names_leads_and_counts():
    fixture = db(
        {
            "leads": [
                {"id": f"l{i}", "name": f"Lead {i}", "status": "new", "created_at": "2026-08-01"}
                for i in range(5)
            ]
        }
    )
    picks = compute_daily_focus(fixture, "t1")
    new_pick = next(p for p in picks if p["kind"] == "new_leads")
    assert new_pick["count"] == 5
    assert "and 2 more" in new_pick["title"]  # 3 named + 2 overflow


def test_broken_table_degrades_to_other_rules():
    """A table that raises must not sink the whole endpoint."""

    class ExplodingDb:
        def table(self, name):
            if name == "leads":
                raise RuntimeError("boom")
            return db({}).table(name)

    assert compute_daily_focus(ExplodingDb(), "t1") == []
