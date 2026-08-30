"""Unit tests for Milestone 8 Calendar/CRM data-plane apply + L2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services import os_calendar_crm as svc


CLIENT = "tenant_test_m8"


def _leads_table():
    table = MagicMock()
    chain = table.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=[])
    table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "lead_new", "name": "Ada", "email": "ada@ex.com", "status": "new"}]
    )
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
    return table


@pytest.fixture(autouse=True)
def _flags_on(monkeypatch):
    monkeypatch.setenv("CALENDAR_ACTIONS_ENABLED", "1")
    monkeypatch.setenv("CRM_ACTIONS_ENABLED", "1")


def test_refuse_when_flags_off(monkeypatch):
    monkeypatch.setenv("CALENDAR_ACTIONS_ENABLED", "0")
    monkeypatch.setenv("CRM_ACTIONS_ENABLED", "0")
    assert svc.refuse_calendar_tool(tool_id="create_calendar_event")
    assert svc.refuse_crm_tool(tool_id="update_customer")


def test_create_customer_dedupes_by_email():
    db = MagicMock()
    existing = {
        "id": "lead_1",
        "name": "Ada",
        "email": "ada@ex.com",
        "phone": None,
        "status": "new",
    }

    def tenant_table(_db, name, _cid):
        t = MagicMock()
        if name == "leads":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[existing]
            )
        return t

    with patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table):
        out = svc.apply_crm_mutations(
            db,
            CLIENT,
            [
                {
                    "id": "lead_tmp",
                    "_op": "create",
                    "name": "Ada Lovelace",
                    "email": "ada@ex.com",
                }
            ],
        )
    assert out[0]["applied"] is True
    assert out[0]["detail"] == "deduplicated"


def test_update_customer_preserves_unspecified_fields():
    db = MagicMock()
    before = {
        "id": "lead_1",
        "name": "Ada",
        "email": "ada@ex.com",
        "phone": "555-0100",
        "status": "new",
    }
    after = {**before, "phone": "555-9999"}

    calls = {"n": 0}

    def tenant_table(_db, name, _cid):
        t = MagicMock()

        def select(*_a, **_k):
            calls["n"] += 1
            chain = MagicMock()
            # first select = before; second = after read-back
            data = [before] if calls["n"] == 1 else [after]
            chain.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=data
            )
            return chain

        t.select.side_effect = select
        t.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[after])
        return t

    with patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table):
        out = svc.apply_crm_mutations(
            db,
            CLIENT,
            [{"id": "lead_1", "_op": "update", "fields": {"phone": "555-9999"}}],
        )
    assert out[0]["applied"] is True
    assert out[0]["detail"] == "updated"


def test_invalid_stage_rejected():
    db = MagicMock()
    before = {"id": "lead_1", "name": "Ada", "status": "new"}

    def tenant_table(_db, name, _cid):
        t = MagicMock()
        if name == "pipeline_stages":
            t.select.return_value.execute.return_value = MagicMock(data=[])
        else:
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[before]
            )
        return t

    with patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table):
        out = svc.apply_crm_mutations(
            db,
            CLIENT,
            [{"id": "lead_1", "_op": "stage", "status": "not_a_real_stage"}],
        )
    assert out[0]["applied"] is False
    assert out[0]["detail"] == "invalid_lead_stage"


def test_calendar_l2_refuses_when_flag_off(monkeypatch):
    monkeypatch.setenv("CALENDAR_ACTIONS_ENABLED", "0")
    out = svc.run_calendar_l2(
        MagicMock(),
        CLIENT,
        {"tool_id": "cancel_calendar_event", "input": {"event_id": "x"}},
    )
    assert out["refused"] is True
    assert out["executed"] is False


def test_wrong_tenant_event_not_found():
    def tenant_table(_db, name, _cid):
        t = MagicMock()
        t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        return t

    with patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table):
        applied, detail, row = svc._cancel_local_event(
            MagicMock(), CLIENT, {"id": "other_tenant_evt"}
        )
    assert applied is False
    assert detail == "event_not_found"
    assert row is None


def test_persist_applies_crm_bundle(monkeypatch):
    """Collecting CRM mutations reach apply_crm_mutations via persist."""
    from backend.services import os_tool_executions as persist_svc
    from backend.tests.fake_supabase_store import FakeSupabase

    monkeypatch.setenv("CRM_ACTIONS_ENABLED", "1")
    db = FakeSupabase(
        {
            "os_tool_executions": [],
            "leads": [
                {
                    "id": "lead_1",
                    "client_id": CLIENT,
                    "name": "Ada",
                    "email": "ada@ex.com",
                    "phone": "555-0100",
                    "status": "new",
                    "notes": None,
                }
            ],
            "pipeline_stages": [],
        }
    )
    record = {
        "toolExecutions": [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "accountId": CLIENT,
                "toolId": "update_customer",
                "riskLevel": 1,
                "mutating": True,
                "requiresApproval": False,
                "approvalState": "not_required",
                "status": "succeeded",
                "input": {"customer_id": "lead_1", "fields": {"phone": "555-9999"}},
                "result": {"customerId": "lead_1"},
                "verificationState": "passed",
                "attempts": 1,
                "createdAt": "2026-08-30T12:00:00Z",
            }
        ],
        "customers": [
            {
                "id": "lead_1",
                "_op": "update",
                "fields": {"phone": "555-9999"},
                "name": "Ada",
                "email": "ada@ex.com",
                "phone": "555-9999",
                "status": "new",
            }
        ],
    }
    persist_svc.persist_tool_executions(db, CLIENT, None, record)
    lead = db.rows("leads")[0]
    assert lead["phone"] == "555-9999"
    assert lead["email"] == "ada@ex.com"
    assert lead["name"] == "Ada"


def test_calendar_busy_fields_fail_closed_without_google_or_appointments():
    from backend.services import agent_os_bridge

    with patch(
        "backend.services.google_calendar.get_integration", return_value=None
    ):
        out = agent_os_bridge._calendar_busy_fields(CLIENT, [])
    assert out["calendarBusy"] == []
    assert "not connected" in (out["calendarAvailabilityError"] or "")
