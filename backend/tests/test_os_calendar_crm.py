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


def test_upsert_local_event_does_not_dedupe_same_slot_different_title():
    """Slot-only single-match must not upsert a different title onto the existing row."""
    db = MagicMock()
    start = "2026-09-06T16:00:00+00:00"
    end = "2026-09-06T17:00:00+00:00"
    old_title = "M8 external smoke m8-ext-oldmarker"
    new_title = "M8 external smoke m8-ext-newmarker"
    existing_appt = {
        "id": "appt_old",
        "start_time": start,
        "end_time": end,
        "notes": old_title,
        "google_event_id": "gcal_old",
        "status": "scheduled",
    }
    created_appt = {
        "id": "appt_new",
        "start_time": start,
        "end_time": end,
        "notes": new_title,
        "google_event_id": "gcal_new",
        "status": "scheduled",
    }

    def tenant_table(_db, name, _cid):
        t = MagicMock()
        if name == "appointments":
            chain = MagicMock()
            chain.eq.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[existing_appt]
            )
            t.select.return_value = chain
            t.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[created_appt]
            )
        return t

    with (
        patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table),
        patch("backend.services.booking.create_appointment", return_value=created_appt) as create,
        patch(
            "backend.services.google_calendar.get_integration",
            return_value={"access_token": "x"},
        ),
        patch(
            "backend.services.google_calendar.create_calendar_event",
            return_value="gcal_new",
        ),
        patch(
            "backend.services.google_calendar.get_calendar_event",
            return_value={"start": start, "status": "confirmed"},
        ),
    ):
        applied, detail, row = svc._upsert_local_event(
            db,
            CLIENT,
            {
                "start": start,
                "end": end,
                "title": new_title,
                "attendees": [{"email": "guest@example.com", "displayName": "Guest"}],
                "sendInvitations": True,
            },
        )

    assert applied is True
    assert detail == "created"
    assert row["id"] == "appt_new"
    assert row["google_event_id"] == "gcal_new"
    create.assert_called_once()


def test_upsert_local_event_dedupes_same_slot_when_title_in_notes():
    """Subsequent write of the same title still matches the existing appointment."""
    db = MagicMock()
    start = "2026-09-06T16:00:00+00:00"
    end = "2026-09-06T17:00:00+00:00"
    title = "Consult — marker m8-cal-abc12345"
    existing_appt = {
        "id": "appt_same",
        "start_time": start,
        "end_time": end,
        "notes": title,
        "google_event_id": "gcal_same",
        "status": "scheduled",
    }

    def tenant_table(_db, name, _cid):
        t = MagicMock()
        if name == "appointments":
            chain = MagicMock()
            chain.eq.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[existing_appt]
            )
            t.select.return_value = chain
        return t

    with (
        patch("backend.services.os_calendar_crm.tenant_table", side_effect=tenant_table),
        patch("backend.services.booking.create_appointment") as create,
    ):
        applied, detail, row = svc._upsert_local_event(
            db,
            CLIENT,
            {
                "start": start,
                "end": end,
                "title": title,
                "description": "Notes: Consult — marker m8-cal-abc12345",
            },
        )

    assert applied is True
    assert detail == "deduplicated"
    assert row["id"] == "appt_same"
    assert row["google_event_id"] == "gcal_same"
    create.assert_not_called()


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
