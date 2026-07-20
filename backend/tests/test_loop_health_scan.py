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
        # A sighted scan always sees tenants; without one the blind-scan
        # guard would (correctly) preempt the suggestion-rot rule.
        "tenants": [_tenant("t1")],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "rotting undecided" in alerts[0]
    assert "2 pending card(s)" in alerts[0]
    assert "oldest 35d" in alerts[0]


def test_blind_scan_pages_instead_of_looking_healthy():
    """Zero tenants = the key cannot read prod (RLS silent-empty). The
    scan must alert rather than report a quiet, healthy-looking run —
    caught live on 2026-07-17 when the Actions secret held the anon key."""
    vitals = {"drafts": [], "suggestions": [], "tenants": []}
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "BLIND" in alerts[0]
    assert "service_role" in alerts[0]


def test_blind_scan_guard_short_circuits_other_rules():
    """With no tenant rows, draft/suggestion data is untrustworthy — only
    the blind alert fires even when rows look rotten."""
    vitals = {
        "drafts": [
            {
                "client_id": "t1",
                "deliverable_status": "pending_approval",
                "updated_at": _iso_days_ago(99),
            }
        ],
        "suggestions": [
            {"status": "pending", "created_at": _iso_days_ago(99)},
        ],
        "tenants": [],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "BLIND" in alerts[0]


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


def test_collect_vitals_queries_four_tables():
    seen = []

    def fake_fetch(table, params):
        seen.append((table, params.get("select")))
        return [{"table": table}]

    vitals = collect_vitals(fake_fetch)
    assert [t for t, _ in seen] == [
        "os_agent_runs",
        "os_backlog_requests",
        "tenants",
        "activity_log",
    ]
    # Drafts query must exclude rows without a deliverable.
    assert vitals["drafts"] == [{"table": "os_agent_runs"}]
    assert vitals["suggestions"] == [{"table": "os_backlog_requests"}]
    assert vitals["tenants"] == [{"table": "tenants"}]
    assert vitals["guard_events"] == [{"table": "activity_log"}]


def test_eval_regression_always_alerts():
    vitals = {
        "drafts": [],
        "suggestions": [],
        "tenants": [_tenant("t1")],
        "guard_events": [
            {"activity_type": "kb_eval_regression", "created_at": _iso_days_ago(1)},
        ],
    }
    alerts = evaluate_alerts(vitals, _NOW)
    assert len(alerts) == 1
    assert "Golden-question regressions: 1" in alerts[0]


def test_guard_holds_alert_only_above_threshold():
    from scripts.loop_health_scan import GUARD_HOLD_ALERT_THRESHOLD

    def _holds(count, age_days=1):
        return [
            {
                "activity_type": "outbound_guard_flagged",
                "created_at": _iso_days_ago(age_days),
            }
            for _ in range(count)
        ]

    base = {"drafts": [], "suggestions": [], "tenants": [_tenant("t1")]}

    quiet = evaluate_alerts(
        {**base, "guard_events": _holds(GUARD_HOLD_ALERT_THRESHOLD)}, _NOW
    )
    assert quiet == []

    noisy = evaluate_alerts(
        {**base, "guard_events": _holds(GUARD_HOLD_ALERT_THRESHOLD + 1)}, _NOW
    )
    assert len(noisy) == 1
    assert "Outbound guard held" in noisy[0]

    # Events older than the 7-day window never count.
    stale = evaluate_alerts(
        {**base, "guard_events": _holds(GUARD_HOLD_ALERT_THRESHOLD + 5, age_days=9)},
        _NOW,
    )
    assert stale == []
