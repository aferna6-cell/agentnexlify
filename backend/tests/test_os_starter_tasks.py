"""Starter tasks for idle Agent OS tenants (cold-start activation).

Contract:
  1. Always exactly 3 starters, each {"label", "prompt"} with non-empty strings.
  2. Data-aware first: tenants with leads get a lead follow-up starter;
     tenants with appointments get a reminder starter.
  3. Generic fillers personalize on tenants.business_type when present.
  4. Never raises — any DB failure degrades to the 3 generic starters.

Why: the AgentOS insights card hid itself for zero-activity tenants
(OsInsightsCard returned null), leaving new owners a blank composer. The
model-call ledger showed 16 drafts ever — activation, not capability, is
the binding constraint.
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.os_starter_tasks import compute_starter_tasks

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _db(leads_count=0, appts_count=0, business_type=None, raise_on=None):
    """Mock Supabase: per-table counts + tenants profile row."""
    db = MagicMock()

    def table_side_effect(name):
        if raise_on == name:
            raise RuntimeError(f"{name} down")
        m = MagicMock()
        for attr in ("select", "eq", "gte", "limit", "in_"):
            getattr(m, attr).return_value = m
        if name == "leads":
            m.execute.return_value = MagicMock(count=leads_count, data=[])
        elif name == "appointments":
            m.execute.return_value = MagicMock(count=appts_count, data=[])
        elif name == "tenants":
            row = {"business_type": business_type} if business_type else {}
            m.execute.return_value = MagicMock(data=[row])
        else:
            m.execute.return_value = MagicMock(count=0, data=[])
        return m

    db.table.side_effect = table_side_effect
    return db


def _assert_shape(starters):
    assert len(starters) == 3
    for s in starters:
        assert s["label"].strip()
        assert s["prompt"].strip()


def test_no_data_tenant_gets_three_generic_starters():
    starters = compute_starter_tasks(_db(), _TENANT)
    _assert_shape(starters)


def test_business_type_personalizes_generic_prompts():
    starters = compute_starter_tasks(_db(business_type="salon"), _TENANT)
    _assert_shape(starters)
    assert any("salon" in s["prompt"] for s in starters)


def test_tenant_with_leads_gets_lead_followup_first():
    starters = compute_starter_tasks(_db(leads_count=4), _TENANT)
    _assert_shape(starters)
    assert "lead" in starters[0]["prompt"].lower()


def test_tenant_with_appointments_gets_reminder_starter():
    starters = compute_starter_tasks(_db(appts_count=2), _TENANT)
    _assert_shape(starters)
    assert any("appointment" in s["prompt"].lower() for s in starters)


def test_db_failure_degrades_to_generic_not_raise():
    starters = compute_starter_tasks(_db(raise_on="leads"), _TENANT)
    _assert_shape(starters)


def test_leads_and_appointments_both_present_still_three():
    starters = compute_starter_tasks(
        _db(leads_count=9, appts_count=3, business_type="plumbing"), _TENANT
    )
    _assert_shape(starters)
    assert "lead" in starters[0]["prompt"].lower()
    assert any("appointment" in s["prompt"].lower() for s in starters)


def test_profile_read_failure_falls_back_to_generic_wording():
    starters = compute_starter_tasks(_db(raise_on="tenants"), _TENANT)
    _assert_shape(starters)
    assert any("business" in s["prompt"] for s in starters)


# --- GET /os/insights gating -------------------------------------------------
def _run_insights(week, suggestions, starters):
    """Call the endpoint with all three compute fns patched."""
    import asyncio
    from unittest.mock import patch

    from backend.routers import os_insights as router_mod

    with (
        patch.object(router_mod, "get_service_supabase", return_value=MagicMock()),
        patch.object(router_mod, "compute_weekly_value", return_value=week),
        patch.object(router_mod, "compute_suggestions", return_value=suggestions),
        patch.object(
            router_mod, "compute_starter_tasks", return_value=starters
        ) as starter_fn,
    ):
        result = asyncio.run(router_mod.get_insights(claims={"tenant_id": _TENANT}))
    return result, starter_fn


_IDLE_WEEK = {
    "leads_captured": 0,
    "appointments_booked": 0,
    "invoices_sent": 0,
    "agent_runs_completed": 0,
}


def test_insights_returns_starters_for_idle_tenant():
    result, starter_fn = _run_insights(_IDLE_WEEK, [], [{"label": "x", "prompt": "y"}])
    starter_fn.assert_called_once()
    assert result["starters"] == [{"label": "x", "prompt": "y"}]


def test_insights_skips_starters_when_active():
    week = dict(_IDLE_WEEK, agent_runs_completed=2)
    result, starter_fn = _run_insights(week, [], [{"label": "x", "prompt": "y"}])
    starter_fn.assert_not_called()
    assert result["starters"] == []


def test_insights_skips_starters_when_suggestions_exist():
    result, starter_fn = _run_insights(
        _IDLE_WEEK, [{"summary": "cold leads"}], [{"label": "x", "prompt": "y"}]
    )
    starter_fn.assert_not_called()
    assert result["starters"] == []
