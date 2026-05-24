"""Unit tests for backend.services.automation.trigger_dispatch — domain-event reactors."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.automation.trigger_dispatch import (
    check_appointment_triggers,
    check_form_submission_triggers,
    check_lead_captured_triggers,
    check_tag_triggers,
    schedule_automation_check,
)


def _chain(result_data):
    """Return a MagicMock whose chained calls all return self until .execute()."""
    table = MagicMock()
    for method in (
        "select",
        "eq",
        "neq",
        "in_",
        "gt",
        "gte",
        "lt",
        "lte",
        "order",
        "limit",
        "range",
        "or_",
        "is_",
    ):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=result_data)
    return table


def _db_with_tables(table_queue):
    """Build a MagicMock db.

    table_queue is a dict mapping table_name -> list of chain MagicMocks. Each call
    to db.table(name) consumes from the head of the queue. Missing tables return
    an empty result chain.
    """
    db = MagicMock()

    def table_side_effect(name):
        if name in table_queue and table_queue[name]:
            return table_queue[name].pop(0)
        return _chain([])

    db.table.side_effect = table_side_effect
    return db


# ---- check_lead_captured_triggers ----


@pytest.mark.asyncio
async def test_check_lead_captured_no_lead_found():
    db = _db_with_tables({"leads": [_chain([])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_lead_captured_triggers("missing-lead")
    assert result == 0


@pytest.mark.asyncio
async def test_check_lead_captured_lead_lookup_throws():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db is down")
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_lead_captured_triggers("lead-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_lead_captured_no_tenant():
    db = _db_with_tables({"leads": [_chain([{"id": "lead-1", "client_id": None}])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_lead_captured_triggers("lead-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_lead_captured_rules_query_throws():
    lead_chain = _chain([{"id": "lead-1", "client_id": "t1"}])
    calls = {"n": 0}
    rules_chain = _chain([])

    def fail_rules(name):
        calls["n"] += 1
        if name == "leads":
            return lead_chain
        if name == "automation_rules":
            raise RuntimeError("rules query failed")
        return rules_chain

    db = MagicMock()
    db.table.side_effect = fail_rules
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_lead_captured_triggers("lead-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_lead_captured_fires_rule():
    lead = {"id": "lead-1", "client_id": "t1", "email": "a@b.com"}
    rule = {"id": "rule-1", "trigger_type": "lead_captured", "conditions": []}
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = {"status": "success"}
        result = await check_lead_captured_triggers("lead-1")
    assert result == 1
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_lead_captured_skips_unmatched_conditions():
    lead = {"id": "lead-1", "client_id": "t1", "email": "a@b.com"}
    rule = {
        "id": "rule-1",
        "trigger_type": "lead_captured",
        "conditions": [{"field": "email", "operator": "equals", "value": "other@b.com"}],
    }
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_lead_captured_triggers("lead-1")
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_lead_captured_execute_throws_continues():
    lead = {"id": "lead-1", "client_id": "t1"}
    rule = {"id": "rule-1", "trigger_type": "lead_captured", "conditions": []}
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.side_effect = RuntimeError("action failed")
        result = await check_lead_captured_triggers("lead-1")
    assert result == 0


# ---- check_tag_triggers ----


@pytest.mark.asyncio
async def test_check_tag_triggers_lead_lookup_fails():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_tag_triggers("t1", "lead-1", "vip", added=True)
    assert result == 0


@pytest.mark.asyncio
async def test_check_tag_triggers_rules_query_fails():
    lead_chain = _chain([{"id": "lead-1", "client_id": "t1"}])

    def side_effect(name):
        if name == "leads":
            return lead_chain
        if name == "automation_rules":
            raise RuntimeError("rules failed")
        return _chain([])

    db = MagicMock()
    db.table.side_effect = side_effect
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_tag_triggers("t1", "lead-1", "vip", added=True)
    assert result == 0


@pytest.mark.asyncio
async def test_check_tag_triggers_fires_matching_tag():
    lead = {"id": "lead-1", "client_id": "t1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "tag_added",
        "trigger_config": {"tag": "vip"},
        "conditions": [],
    }
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_tag_triggers("t1", "lead-1", "vip", added=True)
    assert result == 1
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_tag_triggers_skips_unrelated_tag():
    lead = {"id": "lead-1", "client_id": "t1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "tag_added",
        "trigger_config": {"tag": "cold"},
        "conditions": [],
    }
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_tag_triggers("t1", "lead-1", "vip", added=True)
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_tag_triggers_removal_uses_tag_removed():
    lead = {"id": "lead-1", "client_id": "t1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "tag_removed",
        "trigger_config": {"tag": "vip"},
        "conditions": [],
    }
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_tag_triggers("t1", "lead-1", "vip", added=False)
    assert result == 1


@pytest.mark.asyncio
async def test_check_tag_triggers_execute_throws_continues():
    lead = {"id": "lead-1", "client_id": "t1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "tag_added",
        "trigger_config": {"tag": "vip"},
        "conditions": [],
    }
    db = _db_with_tables({
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.side_effect = RuntimeError("nope")
        result = await check_tag_triggers("t1", "lead-1", "vip", added=True)
    assert result == 0


# ---- check_form_submission_triggers ----


@pytest.mark.asyncio
async def test_check_form_submission_no_submission():
    db = _db_with_tables({"form_submissions": [_chain([])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_form_submission_triggers("missing-sub")
    assert result == 0


@pytest.mark.asyncio
async def test_check_form_submission_load_throws():
    db = MagicMock()
    db.table.side_effect = RuntimeError("submission load failed")
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_form_submission_triggers("sub-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_form_submission_no_tenant():
    db = _db_with_tables({"form_submissions": [_chain([{"id": "sub-1", "tenant_id": None}])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_form_submission_triggers("sub-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_form_submission_lead_fetch_warns_but_continues():
    submission = {"id": "sub-1", "tenant_id": "t1", "lead_id": "lead-1"}

    def side_effect(name):
        if name == "form_submissions":
            return _chain([submission])
        if name == "leads":
            raise RuntimeError("lead lookup failed")
        if name == "automation_rules":
            return _chain([])
        return _chain([])

    db = MagicMock()
    db.table.side_effect = side_effect
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_form_submission_triggers("sub-1", form_id="form-99")
    assert result == 0


@pytest.mark.asyncio
async def test_check_form_submission_rules_query_throws():
    submission = {"id": "sub-1", "tenant_id": "t1", "lead_id": "lead-1"}

    def side_effect(name):
        if name == "form_submissions":
            return _chain([submission])
        if name == "leads":
            return _chain([{"id": "lead-1"}])
        if name == "automation_rules":
            raise RuntimeError("rules failed")
        return _chain([])

    db = MagicMock()
    db.table.side_effect = side_effect
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_form_submission_triggers("sub-1", form_id="form-99")
    assert result == 0


@pytest.mark.asyncio
async def test_check_form_submission_fires_matching():
    submission = {"id": "sub-1", "tenant_id": "t1", "lead_id": "lead-1"}
    lead = {"id": "lead-1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "form_submitted",
        "trigger_config": {"form_id": "form-99"},
        "conditions": [],
    }
    db = _db_with_tables({
        "form_submissions": [_chain([submission])],
        "leads": [_chain([lead])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_form_submission_triggers("sub-1", form_id="form-99")
    assert result == 1
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_form_submission_skips_form_id_mismatch():
    submission = {"id": "sub-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "form_submitted",
        "trigger_config": {"form_id": "form-99"},
        "conditions": [],
    }
    db = _db_with_tables({
        "form_submissions": [_chain([submission])],
        "leads": [_chain([{"id": "lead-1"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_form_submission_triggers("sub-1", form_id="form-other")
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_form_submission_execute_throws_continues():
    submission = {"id": "sub-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "form_submitted",
        "trigger_config": {},
        "conditions": [],
    }
    db = _db_with_tables({
        "form_submissions": [_chain([submission])],
        "leads": [_chain([{"id": "lead-1"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.side_effect = RuntimeError("blew up")
        result = await check_form_submission_triggers("sub-1")
    assert result == 0


# ---- check_appointment_triggers ----


@pytest.mark.asyncio
async def test_check_appointment_no_appointment():
    db = _db_with_tables({"appointments": [_chain([])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_appointment_triggers("missing-appt")
    assert result == 0


@pytest.mark.asyncio
async def test_check_appointment_load_throws():
    db = MagicMock()
    db.table.side_effect = RuntimeError("appointment load failed")
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_appointment_triggers("appt-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_appointment_no_tenant():
    db = _db_with_tables({"appointments": [_chain([{"id": "appt-1", "tenant_id": None}])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_appointment_triggers("appt-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_appointment_lead_lookup_fails_but_continues():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}

    def side_effect(name):
        if name == "appointments":
            return _chain([appt])
        if name == "leads":
            raise RuntimeError("leads down")
        if name == "automation_rules":
            return _chain([])
        return _chain([])

    db = MagicMock()
    db.table.side_effect = side_effect
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_appointment_triggers("appt-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_appointment_rules_query_throws():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}

    def side_effect(name):
        if name == "appointments":
            return _chain([appt])
        if name == "leads":
            return _chain([{"id": "lead-1"}])
        if name == "automation_rules":
            raise RuntimeError("rules failed")
        return _chain([])

    db = MagicMock()
    db.table.side_effect = side_effect
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await check_appointment_triggers("appt-1")
    assert result == 0


@pytest.mark.asyncio
async def test_check_appointment_created_fires():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {"id": "rule-1", "trigger_type": "appointment_created", "conditions": []}
    db = _db_with_tables({
        "appointments": [_chain([appt])],
        "leads": [_chain([{"id": "lead-1"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_appointment_triggers("appt-1", completed=False)
    assert result == 1
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_appointment_completed_fires():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {"id": "rule-1", "trigger_type": "appointment_completed", "conditions": []}
    db = _db_with_tables({
        "appointments": [_chain([appt])],
        "leads": [_chain([{"id": "lead-1"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_appointment_triggers("appt-1", completed=True)
    assert result == 1


@pytest.mark.asyncio
async def test_check_appointment_skips_unmatched_conditions():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {
        "id": "rule-1",
        "trigger_type": "appointment_created",
        "conditions": [{"field": "status", "operator": "equals", "value": "vip"}],
    }
    db = _db_with_tables({
        "appointments": [_chain([appt])],
        "leads": [_chain([{"id": "lead-1", "status": "regular"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        result = await check_appointment_triggers("appt-1")
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_appointment_execute_throws_continues():
    appt = {"id": "appt-1", "tenant_id": "t1", "lead_id": "lead-1"}
    rule = {"id": "rule-1", "trigger_type": "appointment_created", "conditions": []}
    db = _db_with_tables({
        "appointments": [_chain([appt])],
        "leads": [_chain([{"id": "lead-1"}])],
        "automation_rules": [_chain([rule])],
    })
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.side_effect = RuntimeError("kaboom")
        result = await check_appointment_triggers("appt-1")
    assert result == 0


# ---- schedule_automation_check ----


@pytest.mark.asyncio
async def test_schedule_automation_check_no_rules():
    db = _db_with_tables({"automation_rules": [_chain([])]})
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await schedule_automation_check()
    assert result == 0


@pytest.mark.asyncio
async def test_schedule_automation_check_rules_query_throws():
    db = MagicMock()
    db.table.side_effect = RuntimeError("query failed")
    with patch("backend.services.automation.trigger_dispatch.get_service_supabase", return_value=db):
        result = await schedule_automation_check()
    assert result == 0


@pytest.mark.asyncio
async def test_schedule_automation_check_daily_match_fires():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday 09:00 UTC
    rule = {
        "id": "rule-daily",
        "tenant_id": "t1",
        "trigger_type": "scheduled_daily",
        "trigger_config": {"time": "09:00", "days": ["tue"]},
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        # Re-export timezone so the source-line `timezone.utc` reference resolves
        mock_dt.timezone = timezone  # noqa
        result = await schedule_automation_check()
    assert result == 1
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_schedule_automation_check_daily_wrong_day_skips():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday
    rule = {
        "id": "rule-daily",
        "tenant_id": "t1",
        "trigger_type": "scheduled_daily",
        "trigger_config": {"time": "09:00", "days": ["mon"]},
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        result = await schedule_automation_check()
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_automation_check_weekly_match_fires():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 6, 9, 0, tzinfo=timezone.utc)  # Monday
    rule = {
        "id": "rule-weekly",
        "tenant_id": "t1",
        "trigger_type": "scheduled_weekly",
        "trigger_config": {"day": "monday", "time": "09:00"},
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        result = await schedule_automation_check()
    assert result == 1


@pytest.mark.asyncio
async def test_schedule_automation_check_weekly_wrong_day_skips():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday
    rule = {
        "id": "rule-weekly",
        "tenant_id": "t1",
        "trigger_type": "scheduled_weekly",
        "trigger_config": {"day": "monday", "time": "09:00"},
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        result = await schedule_automation_check()
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_automation_check_already_fired_today_skips():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday
    rule = {
        "id": "rule-daily",
        "tenant_id": "t1",
        "trigger_type": "scheduled_daily",
        "trigger_config": {"time": "09:00", "days": ["tue"]},
        "last_triggered_at": "2026-04-07T08:55:00+00:00",
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        result = await schedule_automation_check()
    assert result == 0
    mock_exec.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_automation_check_execute_throws_continues():
    from datetime import datetime, timezone

    fake_now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday
    rule = {
        "id": "rule-daily",
        "tenant_id": "t1",
        "trigger_type": "scheduled_daily",
        "trigger_config": {"time": "09:00", "days": ["tue"]},
    }
    db = _db_with_tables({"automation_rules": [_chain([rule])]})
    with patch(
        "backend.services.automation.trigger_dispatch.get_service_supabase",
        return_value=db,
    ), patch(
        "backend.services.automation.trigger_dispatch.execute_automation_rule",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "backend.services.automation.trigger_dispatch.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_exec.side_effect = RuntimeError("execute failed")
        result = await schedule_automation_check()
    assert result == 0
