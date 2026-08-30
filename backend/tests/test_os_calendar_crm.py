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
