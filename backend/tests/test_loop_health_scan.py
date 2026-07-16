"""Unit tests for scripts/loop_health_scan.py (daily digest loop-health job).

Contract:

  1. Sweep-rot alert fires only for pending_approval drafts older than 16
     days on ACTIVE PAID tenants — free/lapsed tenants are the sweep's
     documented out-of-scope and must not page anyone.
  2. Suggestion-rot alert fires when the oldest pending card exceeds 21
     days; decided/superseded cards never count.
  3. Quiet state -> no alerts; report renders alerts + vitals when noisy.
  4. collect_vitals issues the three expected REST queries through the
     injected fetcher.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.loop_health_scan import (
    SUGGESTION_ROT_DAYS,
    SWEEP_ROT_DAYS,
    collect_vitals,
    evaluate_alerts,
    render_report,
    summarize,
)

_NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)


def _iso_days_ago(days: float) -> str:
    return (_NOW - timedelta(days=days)).isoformat()


def _tenant(tid, plan="agent_os", status="active", name="Acme"):
    return {"id": tid, "plan": plan, "plan_status": status, "business_name": name}


def test_sweep_rot_fires_for_old_paid_tenant_draft():
    vitals = {
        "drafts": [
            {
                "client_id": "t1",
                "deliverable_status": "pending_approval",
                "updated_at": _iso_days_ago(SWEEP_ROT_DAYS + 10),
            },
        ],
        "suggestions": [],
        "tenants": [_tenant("t1", name="Acme Plumbing")],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "Expiry sweep" in alerts[0]
    assert "Acme Plumbing" in alerts[0]
    assert "oldest 26d" in alerts[0]


def test_sweep_rot_ignores_free_and_lapsed_tenants():
    vitals = {
        "drafts": [
            {
                "client_id": "free-t",
                "deliverable_status": "pending_approval",
                "updated_at": _iso_days_ago(40),
            },
            {
                "client_id": "lapsed-t",
                "deliverable_status": "pending_approval",
                "updated_at": _iso_days_ago(40),
            },
        ],
        "suggestions": [],
        "tenants": [
            _tenant("free-t", plan="free"),
            _tenant("lapsed-t", plan="agent_os", status="paused"),
        ],
    }
    assert evaluate_alerts(vitals, _NOW) == []


def test_sweep_rot_ignores_fresh_and_non_pending_drafts():
    vitals = {
        "drafts": [
            {
                "client_id": "t1",
                "deliverable_status": "pending_approval",
                "updated_at": _iso_days_ago(SWEEP_ROT_DAYS - 2),
            },
            {
                "client_id": "t1",
                "deliverable_status": "expired",
                "updated_at": _iso_days_ago(60),
            },
        ],
        "suggestions": [],
        "tenants": [_tenant("t1")],
    }
    assert evaluate_alerts(vitals, _NOW) == []


def test_suggestion_rot_counts_only_old_pending_cards():
    vitals = {
        "drafts": [],
        "suggestions": [
            {"status": "pending", "created_at": _iso_days_ago(SUGGESTION_ROT_DAYS + 14)},
            {"status": "pending", "created_at": _iso_days_ago(SUGGESTION_ROT_DAYS + 2)},
            {"status": "pending", "created_at": _iso_days_ago(3)},
            {"status": "superseded", "created_at": _iso_days_ago(90)},
            {"status": "accepted", "created_at": _iso_days_ago(90)},
        ],
        "tenants": [],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "rotting undecided" in alerts[0]
    assert "2 pending card(s)" in alerts[0]
    assert "oldest 35d" in alerts[0]


def test_quiet_state_produces_no_alerts():
    vitals = {
        "drafts": [
            {
                "client_id": "t1",
                "deliverable_status": "approved",
                "updated_at": _iso_days_ago(100),
            }
        ],
        "suggestions": [{"status": "pending", "created_at": _iso_days_ago(1)}],
        "tenants": [_tenant("t1")],
    }
    assert evaluate_alerts(vitals, _NOW) == []


def test_render_report_includes_alerts_and_vitals():
    vitals = {
        "drafts": [
            {"client_id": "t1", "deliverable_status": "expired", "updated_at": _iso_days_ago(1)},
            {"client_id": "t1", "deliverable_status": "expired", "updated_at": _iso_days_ago(2)},
        ],
        "suggestions": [{"status": "pending", "created_at": _iso_days_ago(30)}],
        "tenants": [_tenant("t1")],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    report = render_report(alerts, vitals, _NOW)
    assert "Agent OS loop health -- 2026-07-16" in report
    assert "rotting undecided" in report
    assert '"expired": 2' in report
    assert '"pending": 1' in report
    assert "/api/v1/admin/loop-health" in report


def test_summarize_counts_by_status():
    line = summarize(
        {
            "drafts": [
                {"deliverable_status": "pending_approval"},
                {"deliverable_status": "pending_approval"},
                {"deliverable_status": None},
            ],
            "suggestions": [{"status": "pending"}],
        }
    )
    assert '"pending_approval": 2' in line
    assert '"unknown": 1' in line
    assert '"pending": 1' in line


def test_collect_vitals_queries_three_tables():
    seen = []

    def fake_fetch(table, params):
        seen.append((table, params.get("select")))
        return [{"table": table}]

    vitals = collect_vitals(fake_fetch)
    assert [t for t, _ in seen] == ["os_agent_runs", "os_backlog_requests", "tenants"]
    # Drafts query must exclude rows without a deliverable.
    assert vitals["drafts"] == [{"table": "os_agent_runs"}]
    assert vitals["suggestions"] == [{"table": "os_backlog_requests"}]
    assert vitals["tenants"] == [{"table": "tenants"}]
