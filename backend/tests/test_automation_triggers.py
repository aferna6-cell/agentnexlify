"""Unit tests for backend.services.automation.triggers — pure trigger evaluation."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from backend.services.automation.triggers import (
    _evaluate_conditions,
    _get_nested_field,
    _parse_utc_datetime,
    _scheduled_rule_already_fired,
    evaluate_trigger,
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


def _db_with_tables(tables):
    """Build a MagicMock db where db.table(name) returns the configured chain."""
    db = MagicMock()

    def table_side_effect(name):
        if name in tables:
            entry = tables[name]
            if isinstance(entry, list):
                if entry:
                    return entry.pop(0)
                return _chain([])
            return entry
        return _chain([])

    db.table.side_effect = table_side_effect
    return db


# ---- _get_nested_field ----


def test_get_nested_field_returns_top_level():
    assert _get_nested_field({"email": "a@b.com"}, "email") == "a@b.com"


def test_get_nested_field_handles_dot_notation():
    data = {"profile": {"address": {"city": "Boston"}}}
    assert _get_nested_field(data, "profile.address.city") == "Boston"


def test_get_nested_field_returns_none_for_missing():
    assert _get_nested_field({"a": 1}, "b") is None


def test_get_nested_field_returns_none_when_traversing_non_dict():
    assert _get_nested_field({"a": "string"}, "a.b") is None


# ---- _evaluate_conditions ----


def test_evaluate_conditions_empty_list_returns_true():
    assert _evaluate_conditions([], {"id": "x"}) is True


def test_evaluate_conditions_no_lead_returns_false():
    assert _evaluate_conditions([{"field": "x", "operator": "equals", "value": 1}], None) is False


def test_evaluate_conditions_equals_passes():
    conds = [{"field": "email", "operator": "equals", "value": "a@b.com"}]
    assert _evaluate_conditions(conds, {"email": "a@b.com"}) is True


def test_evaluate_conditions_equals_fails():
    conds = [{"field": "email", "operator": "equals", "value": "a@b.com"}]
    assert _evaluate_conditions(conds, {"email": "other@b.com"}) is False


def test_evaluate_conditions_not_equals():
    conds = [{"field": "email", "operator": "not_equals", "value": "a@b.com"}]
    assert _evaluate_conditions(conds, {"email": "other@b.com"}) is True
    assert _evaluate_conditions(conds, {"email": "a@b.com"}) is False


def test_evaluate_conditions_contains():
    conds = [{"field": "name", "operator": "contains", "value": "Smith"}]
    assert _evaluate_conditions(conds, {"name": "John Smith"}) is True
    assert _evaluate_conditions(conds, {"name": "John Doe"}) is False


def test_evaluate_conditions_not_contains():
    conds = [{"field": "name", "operator": "not_contains", "value": "Smith"}]
    assert _evaluate_conditions(conds, {"name": "John Doe"}) is True
    assert _evaluate_conditions(conds, {"name": "John Smith"}) is False


def test_evaluate_conditions_greater_than():
    conds = [{"field": "score", "operator": "greater_than", "value": 50}]
    assert _evaluate_conditions(conds, {"score": 75}) is True
    assert _evaluate_conditions(conds, {"score": 25}) is False


def test_evaluate_conditions_greater_than_bad_value():
    conds = [{"field": "score", "operator": "greater_than", "value": 50}]
    assert _evaluate_conditions(conds, {"score": "not_a_number"}) is False


def test_evaluate_conditions_less_than():
    conds = [{"field": "score", "operator": "less_than", "value": 50}]
    assert _evaluate_conditions(conds, {"score": 25}) is True
    assert _evaluate_conditions(conds, {"score": 75}) is False


def test_evaluate_conditions_less_than_bad_value():
    conds = [{"field": "score", "operator": "less_than", "value": 50}]
    assert _evaluate_conditions(conds, {"score": None}) is False


def test_evaluate_conditions_is_empty():
    conds = [{"field": "phone", "operator": "is_empty"}]
    assert _evaluate_conditions(conds, {"phone": None}) is True
    assert _evaluate_conditions(conds, {"phone": ""}) is True
    assert _evaluate_conditions(conds, {"phone": []}) is True
    assert _evaluate_conditions(conds, {"phone": "555-1234"}) is False


def test_evaluate_conditions_is_not_empty():
    conds = [{"field": "phone", "operator": "is_not_empty"}]
    assert _evaluate_conditions(conds, {"phone": "555-1234"}) is True
    assert _evaluate_conditions(conds, {"phone": None}) is False
    assert _evaluate_conditions(conds, {"phone": ""}) is False


def test_evaluate_conditions_multiple_AND():
    conds = [
        {"field": "score", "operator": "greater_than", "value": 50},
        {"field": "email", "operator": "contains", "value": "@"},
    ]
    assert _evaluate_conditions(conds, {"score": 75, "email": "a@b.com"}) is True
    assert _evaluate_conditions(conds, {"score": 75, "email": "noatsign"}) is False


def test_evaluate_conditions_unknown_operator_passes():
    # Unknown operator falls through — no clause asserts false, returns True
    conds = [{"field": "x", "operator": "unknown_op", "value": 1}]
    assert _evaluate_conditions(conds, {"x": 1}) is True


# ---- _parse_utc_datetime ----


def test_parse_utc_datetime_none():
    assert _parse_utc_datetime(None) is None
    assert _parse_utc_datetime("") is None


def test_parse_utc_datetime_z_suffix():
    parsed = _parse_utc_datetime("2026-04-07T09:00:00Z")
    assert parsed == datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)


def test_parse_utc_datetime_offset_suffix():
    parsed = _parse_utc_datetime("2026-04-07T09:00:00+00:00")
    assert parsed == datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)


def test_parse_utc_datetime_naive_becomes_utc():
    parsed = _parse_utc_datetime("2026-04-07T09:00:00")
    assert parsed == datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)


def test_parse_utc_datetime_garbage_returns_none():
    assert _parse_utc_datetime("not a date") is None


# ---- _scheduled_rule_already_fired ----


def test_scheduled_rule_never_fired():
    assert _scheduled_rule_already_fired({"trigger_type": "scheduled_daily"}, datetime.now(timezone.utc)) is False


def test_scheduled_rule_daily_fired_today():
    now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)
    rule = {"trigger_type": "scheduled_daily", "last_triggered_at": "2026-04-07T08:00:00+00:00"}
    assert _scheduled_rule_already_fired(rule, now) is True


def test_scheduled_rule_daily_fired_yesterday():
    now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)
    rule = {"trigger_type": "scheduled_daily", "last_triggered_at": "2026-04-06T08:00:00+00:00"}
    assert _scheduled_rule_already_fired(rule, now) is False


def test_scheduled_rule_weekly_same_week():
    now = datetime(2026, 4, 9, 9, 0, tzinfo=timezone.utc)  # Thursday
    rule = {"trigger_type": "scheduled_weekly", "last_triggered_at": "2026-04-06T08:00:00+00:00"}  # Mon same week
    assert _scheduled_rule_already_fired(rule, now) is True


def test_scheduled_rule_weekly_prior_week():
    now = datetime(2026, 4, 9, 9, 0, tzinfo=timezone.utc)
    rule = {"trigger_type": "scheduled_weekly", "last_triggered_at": "2026-03-30T08:00:00+00:00"}
    assert _scheduled_rule_already_fired(rule, now) is False


def test_scheduled_rule_non_scheduled_type_returns_false():
    now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)
    rule = {"trigger_type": "lead_captured", "last_triggered_at": "2026-04-07T08:00:00+00:00"}
    assert _scheduled_rule_already_fired(rule, now) is False


# ---- evaluate_trigger ----


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_captured_true():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "client_id": "t1"}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, lead = await evaluate_trigger("lead_captured", {}, "t1", "lead-1", {})
    assert matched is True
    assert lead == {"id": "lead-1", "client_id": "t1"}


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_captured_no_lead_id():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, lead = await evaluate_trigger("lead_captured", {}, "t1", None, {})
    assert matched is False
    assert lead is None


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_lookup_exception_continues():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, lead = await evaluate_trigger("scheduled_daily", {}, "t1", "lead-1", {})
    assert matched is True
    assert lead is None


@pytest.mark.asyncio
async def test_evaluate_trigger_tag_added_match():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "tags": ["vip", "hot"]}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("tag_added", {"tag": "vip"}, "t1", "lead-1", {})
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_tag_added_no_match():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "tags": ["cold"]}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("tag_added", {"tag": "vip"}, "t1", "lead-1", {})
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_tag_added_no_lead_data():
    db = _db_with_tables({"leads": _chain([])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("tag_added", {"tag": "vip"}, "t1", "lead-1", {})
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_tag_removed_always_false():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1"}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("tag_removed", {"tag": "vip"}, "t1", "lead-1", {})
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_form_submitted_match():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "form_submitted",
            {"form_id": "form-99"},
            "t1",
            None,
            {"form_id": "form-99"},
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_form_submitted_no_match():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "form_submitted",
            {"form_id": "form-99"},
            "t1",
            None,
            {"form_id": "other"},
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_appointment_created_match():
    db = _db_with_tables({"appointments": _chain([{"id": "appt-1", "status": "booked"}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "appointment_created", {}, "t1", None, {"appointment_id": "appt-1"}
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_appointment_completed_no_match():
    db = _db_with_tables({"appointments": _chain([{"id": "appt-1", "status": "booked"}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "appointment_completed", {}, "t1", None, {"appointment_id": "appt-1"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_appointment_no_id_in_context():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("appointment_created", {}, "t1", None, {})
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_appointment_lookup_fails():
    db = MagicMock()

    def side_effect(name):
        if name == "appointments":
            raise RuntimeError("db blew up")
        return _chain([])

    db.table.side_effect = side_effect
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "appointment_created", {}, "t1", None, {"appointment_id": "appt-1"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_appointment_no_row():
    db = _db_with_tables({"appointments": _chain([])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "appointment_created", {}, "t1", None, {"appointment_id": "appt-x"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_pipeline_stage_changed_match():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "pipeline_stage_changed",
            {"from_stage": "new", "to_stage": "qualified"},
            "t1",
            None,
            {"from_stage": "new", "to_stage": "qualified"},
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_pipeline_stage_changed_from_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "pipeline_stage_changed",
            {"from_stage": "new"},
            "t1",
            None,
            {"from_stage": "other"},
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_pipeline_stage_changed_to_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "pipeline_stage_changed",
            {"to_stage": "qualified"},
            "t1",
            None,
            {"to_stage": "other"},
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_pipeline_stage_changed_no_constraints():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "pipeline_stage_changed", {}, "t1", None, {}
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_score_above():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "lead_score": 80}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "lead_score_threshold",
            {"direction": "above", "threshold": 50},
            "t1",
            "lead-1",
            {},
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_score_below():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "lead_score": 20}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "lead_score_threshold",
            {"direction": "below", "threshold": 50},
            "t1",
            "lead-1",
            {},
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_score_no_lead():
    db = _db_with_tables({"leads": _chain([])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "lead_score_threshold",
            {"direction": "above", "threshold": 50},
            "t1",
            "missing",
            {},
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_lead_score_unknown_direction():
    db = _db_with_tables({"leads": _chain([{"id": "lead-1", "lead_score": 80}])})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "lead_score_threshold",
            {"direction": "sideways", "threshold": 50},
            "t1",
            "lead-1",
            {},
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_email_opened_match_when_no_filter():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("email_opened", {}, "t1", None, {})
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_email_opened_campaign_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "email_opened", {"campaign_id": "c1"}, "t1", None, {"campaign_id": "c2"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_email_opened_sequence_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "email_opened", {"sequence_id": "s1"}, "t1", None, {"sequence_id": "s2"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_email_clicked_filter_match():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "email_clicked", {"campaign_id": "c1"}, "t1", None, {"campaign_id": "c1"}
        )
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_email_clicked_campaign_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "email_clicked", {"campaign_id": "c1"}, "t1", None, {"campaign_id": "c2"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_email_clicked_sequence_mismatch():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger(
            "email_clicked", {"sequence_id": "s1"}, "t1", None, {"sequence_id": "s2"}
        )
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_scheduled_daily_always_true():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("scheduled_daily", {}, "t1", None, {})
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_scheduled_weekly_always_true():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("scheduled_weekly", {}, "t1", None, {})
    assert matched is True


@pytest.mark.asyncio
async def test_evaluate_trigger_smart_list_matched_false():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("smart_list_matched", {}, "t1", None, {})
    assert matched is False


@pytest.mark.asyncio
async def test_evaluate_trigger_unknown_type():
    db = _db_with_tables({})
    with patch("backend.services.automation.triggers.get_service_supabase", return_value=db):
        matched, _ = await evaluate_trigger("nope_no_such_trigger", {}, "t1", None, {})
    assert matched is False
