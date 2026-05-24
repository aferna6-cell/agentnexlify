"""Automation trigger evaluation — pure condition/match logic, no action execution."""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


async def evaluate_trigger(
    trigger_type: str,
    trigger_config: dict,
    tenant_id: str,
    lead_id: str | None = None,
    context: dict | None = None,
) -> tuple[bool, dict | None]:
    """Evaluate whether a trigger condition is met for a given lead/context.

    Returns (matches, lead_data) where lead_data is the lead record if a lead
    was involved in the evaluation.
    """
    db = get_service_supabase()
    context = context or {}
    lead_data = None

    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id).select("*").eq("id", lead_id).limit(1).execute()
            )
            lead_data = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.warning("evaluate_trigger: failed to load lead %s", lead_id)

    if trigger_type == "lead_captured":
        return bool(lead_id and lead_data), lead_data

    elif trigger_type == "tag_added":
        target_tag = trigger_config.get("tag", "")
        if not lead_data:
            return False, None
        lead_tags = lead_data.get("tags") or []
        return target_tag in lead_tags, lead_data

    elif trigger_type == "tag_removed":
        return False, lead_data

    elif trigger_type == "form_submitted":
        target_form_id = trigger_config.get("form_id")
        submitted_form_id = context.get("form_id")
        return submitted_form_id == target_form_id, lead_data

    elif trigger_type in ("appointment_created", "appointment_completed"):
        appt_id = context.get("appointment_id")
        if not appt_id:
            return False, None
        try:
            appt_result = (
                tenant_table(db, "appointments", tenant_id)
                .select("id, status")
                .eq("id", appt_id)
                .limit(1)
                .execute()
            )
            if not appt_result.data:
                return False, None
            appt = appt_result.data[0]
            expected_status = (
                "booked" if trigger_type == "appointment_created" else "completed"
            )
            return appt.get("status") == expected_status, lead_data
        except Exception:
            return False, None

    elif trigger_type == "pipeline_stage_changed":
        from_stage = trigger_config.get("from_stage")
        to_stage = trigger_config.get("to_stage")
        ctx_from = context.get("from_stage")
        ctx_to = context.get("to_stage")
        if from_stage and ctx_from != from_stage:
            return False, lead_data
        if to_stage and ctx_to != to_stage:
            return False, lead_data
        return True, lead_data

    elif trigger_type == "lead_score_threshold":
        direction = trigger_config.get("direction")
        threshold = float(trigger_config.get("threshold", 0))
        if not lead_data:
            return False, None
        score = float(lead_data.get("lead_score") or 0)
        if direction == "above":
            return score > threshold, lead_data
        elif direction == "below":
            return score < threshold, lead_data
        return False, lead_data

    elif trigger_type == "email_opened":
        campaign_id = trigger_config.get("campaign_id")
        sequence_id = trigger_config.get("sequence_id")
        event_campaign_id = context.get("campaign_id")
        event_sequence_id = context.get("sequence_id")
        if campaign_id and event_campaign_id != campaign_id:
            return False, lead_data
        if sequence_id and event_sequence_id != sequence_id:
            return False, lead_data
        return True, lead_data

    elif trigger_type == "email_clicked":
        campaign_id = trigger_config.get("campaign_id")
        sequence_id = trigger_config.get("sequence_id")
        event_campaign_id = context.get("campaign_id")
        event_sequence_id = context.get("sequence_id")
        if campaign_id and event_campaign_id != campaign_id:
            return False, lead_data
        if sequence_id and event_sequence_id != sequence_id:
            return False, lead_data
        return True, lead_data

    elif trigger_type == "scheduled_daily":
        return True, None

    elif trigger_type == "scheduled_weekly":
        return True, None

    elif trigger_type == "smart_list_matched":
        return False, lead_data

    else:
        logger.warning("evaluate_trigger: unknown trigger_type %s", trigger_type)
        return False, None


def _evaluate_conditions(conditions: list[dict], lead_data: dict | None) -> bool:
    """Evaluate a list of AND conditions against a lead record."""
    if not conditions:
        return True
    if not lead_data:
        return False

    for cond in conditions:
        field = cond.get("field", "")
        operator = cond.get("operator", "")
        value = cond.get("value")

        field_value = _get_nested_field(lead_data, field)
        operator = str(operator)

        if operator == "equals":
            if str(field_value) != str(value):
                return False
        elif operator == "not_equals":
            if str(field_value) == str(value):
                return False
        elif operator == "contains":
            if str(value) not in str(field_value):
                return False
        elif operator == "not_contains":
            if str(value) in str(field_value):
                return False
        elif operator == "greater_than":
            try:
                if float(field_value) <= float(value):
                    return False
            except (TypeError, ValueError):
                return False
        elif operator == "less_than":
            try:
                if float(field_value) >= float(value):
                    return False
            except (TypeError, ValueError):
                return False
        elif operator == "is_empty":
            if field_value not in (None, "", [], {}):
                return False
        elif operator == "is_not_empty":
            if field_value in (None, "", [], {}):
                return False

    return True


def _get_nested_field(data: dict, field: str) -> Any:
    """Get a field from a dict, supporting dot notation for nested fields."""
    parts = field.split(".")
    value = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _parse_utc_datetime(value: str | None) -> datetime | None:
    """Parse a database timestamp and normalize it to UTC."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _scheduled_rule_already_fired(rule: dict, now: datetime) -> bool:
    """Return True when a scheduled rule already fired in its current period."""
    last_triggered = _parse_utc_datetime(rule.get("last_triggered_at"))
    if not last_triggered:
        return False

    now = now.astimezone(timezone.utc)
    trigger_type = rule.get("trigger_type")
    if trigger_type == "scheduled_daily":
        return last_triggered.date() == now.date()
    if trigger_type == "scheduled_weekly":
        return last_triggered.isocalendar()[:2] == now.isocalendar()[:2]
    return False
