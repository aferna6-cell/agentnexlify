"""Trigger-event dispatch — react to domain events and fire matching automation rules."""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.automation.rule_engine import execute_automation_rule
from backend.services.automation.triggers import (
    _evaluate_conditions,
    _scheduled_rule_already_fired,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


async def check_lead_captured_triggers(lead_id: str) -> int:
    """Check and fire automation rules when a lead is captured."""
    db = get_service_supabase()
    triggered = 0

    try:
        lead_result = db.table("leads").select("*").eq("id", lead_id).limit(1).execute()
        if not lead_result.data:
            return 0
        lead_data = lead_result.data[0]
        tenant_id = lead_data.get("client_id")
    except Exception:
        logger.exception(
            "check_lead_captured_triggers: failed to load lead %s", lead_id
        )
        return 0

    if not tenant_id:
        return 0

    try:
        rules_result = (
            tenant_table(db, "automation_rules", tenant_id)
            .select("*")
            .eq("trigger_type", "lead_captured")
            .eq("is_active", True)
            .order("priority", desc=True)
            .execute()
        )
        rules = rules_result.data or []
    except Exception:
        logger.exception(
            "check_lead_captured_triggers: failed to load rules for tenant %s",
            tenant_id,
        )
        return 0

    for rule in rules:
        conditions = rule.get("conditions") or []
        if not _evaluate_conditions(conditions, lead_data):
            continue
        try:
            await execute_automation_rule(
                rule["id"], lead_id, {"trigger": "lead_captured"}
            )
            triggered += 1
        except Exception:
            logger.exception(
                "check_lead_captured_triggers: failed to execute rule %s", rule["id"]
            )

    return triggered


async def check_tag_triggers(
    tenant_id: str, lead_id: str, tag: str, added: bool = True
) -> int:
    """Check and fire automation rules when a tag is added or removed from a lead."""
    db = get_service_supabase()
    triggered = 0
    trigger_type = "tag_added" if added else "tag_removed"

    try:
        lead_result = tenant_table(db, "leads", tenant_id).select("*").eq("id", lead_id).limit(1).execute()
        lead_data = lead_result.data[0] if lead_result.data else None
    except Exception:
        logger.exception("check_tag_triggers: failed to load lead %s", lead_id)
        return 0

    try:
        rules_result = (
            tenant_table(db, "automation_rules", tenant_id)
            .select("*")
            .eq("trigger_type", trigger_type)
            .eq("is_active", True)
            .order("priority", desc=True)
            .execute()
        )
        rules = rules_result.data or []
    except Exception:
        logger.exception(
            "check_tag_triggers: failed to load rules for tenant %s", tenant_id
        )
        return 0

    for rule in rules:
        rule_tag = (rule.get("trigger_config") or {}).get("tag", "")
        if rule_tag and rule_tag != tag:
            continue
        conditions = rule.get("conditions") or []
        if not _evaluate_conditions(conditions, lead_data):
            continue
        try:
            await execute_automation_rule(
                rule["id"], lead_id, {"trigger": trigger_type, "tag": tag}
            )
            triggered += 1
        except Exception:
            logger.exception(
                "check_tag_triggers: failed to execute rule %s", rule["id"]
            )

    return triggered


async def check_form_submission_triggers(
    submission_id: str, form_id: str | None = None
) -> int:
    """Check and fire automation rules when a form is submitted."""
    db = get_service_supabase()
    triggered = 0

    try:
        form_result = (
            db.table("form_submissions")
            .select("*")
            .eq("id", submission_id)
            .limit(1)
            .execute()
        )
        if not form_result.data:
            return 0
        submission = form_result.data[0]
        tenant_id = submission.get("tenant_id")
        lead_id = submission.get("lead_id")
    except Exception:
        logger.exception(
            "check_form_submission_triggers: failed to load submission %s",
            submission_id,
        )
        return 0

    if not tenant_id:
        return 0

    lead_data = None
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id).select("*").eq("id", lead_id).limit(1).execute()
            )
            lead_data = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.warning("Failed to fetch lead data for automation", exc_info=True)

    try:
        rules_result = (
            tenant_table(db, "automation_rules", tenant_id)
            .select("*")
            .eq("trigger_type", "form_submitted")
            .eq("is_active", True)
            .order("priority", desc=True)
            .execute()
        )
        rules = rules_result.data or []
    except Exception:
        logger.exception(
            "check_form_submission_triggers: failed to load rules for tenant %s",
            tenant_id,
        )
        return 0

    for rule in rules:
        config_form_id = (rule.get("trigger_config") or {}).get("form_id")
        if config_form_id and config_form_id != form_id:
            continue
        conditions = rule.get("conditions") or []
        if not _evaluate_conditions(conditions, lead_data):
            continue
        try:
            await execute_automation_rule(
                rule["id"],
                lead_id,
                {
                    "trigger": "form_submitted",
                    "form_id": form_id,
                    "submission_id": submission_id,
                },
            )
            triggered += 1
        except Exception:
            logger.exception(
                "check_form_submission_triggers: failed to execute rule %s", rule["id"]
            )

    return triggered


async def check_appointment_triggers(
    appointment_id: str, completed: bool = False
) -> int:
    """Check and fire automation rules when an appointment is completed."""
    db = get_service_supabase()
    triggered = 0

    try:
        appt_result = (
            db.table("appointments")
            .select("*")
            .eq("id", appointment_id)
            .limit(1)
            .execute()
        )
        if not appt_result.data:
            return 0
        appointment = appt_result.data[0]
        tenant_id = appointment.get("tenant_id")
        lead_id = appointment.get("lead_id")
    except Exception:
        logger.exception(
            "check_appointment_triggers: failed to load appointment %s", appointment_id
        )
        return 0

    if not tenant_id:
        return 0

    lead_data = None
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id).select("*").eq("id", lead_id).limit(1).execute()
            )
            lead_data = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.warning("Failed to fetch lead data for automation", exc_info=True)

    trigger_type = "appointment_completed" if completed else "appointment_created"

    try:
        rules_result = (
            tenant_table(db, "automation_rules", tenant_id)
            .select("*")
            .eq("trigger_type", trigger_type)
            .eq("is_active", True)
            .order("priority", desc=True)
            .execute()
        )
        rules = rules_result.data or []
    except Exception:
        logger.exception(
            "check_appointment_triggers: failed to load rules for tenant %s", tenant_id
        )
        return 0

    for rule in rules:
        conditions = rule.get("conditions") or []
        if not _evaluate_conditions(conditions, lead_data):
            continue
        try:
            await execute_automation_rule(
                rule["id"],
                lead_id,
                {"trigger": trigger_type, "appointment_id": appointment_id},
            )
            triggered += 1
        except Exception:
            logger.exception(
                "check_appointment_triggers: failed to execute rule %s", rule["id"]
            )

    return triggered


async def schedule_automation_check() -> int:
    """Periodic check for scheduled automation triggers (daily/weekly).

    Called every 5 minutes from the automation loop to evaluate
    scheduled_daily and scheduled_weekly triggers.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    triggered = 0

    try:
        rules_result = (
            db.table("automation_rules")
            .select("*")
            .eq("is_active", True)
            .in_("trigger_type", ["scheduled_daily", "scheduled_weekly"])
            .execute()
        )
        rules = rules_result.data or []
    except Exception:
        logger.exception("schedule_automation_check: failed to load scheduled rules")
        return 0

    for rule in rules:
        tenant_id = rule.get("tenant_id")
        trigger_type = rule.get("trigger_type")
        trigger_config = rule.get("trigger_config") or {}

        should_fire = False
        if trigger_type == "scheduled_daily":
            target_time = trigger_config.get("time", "09:00")
            target_days = trigger_config.get(
                "days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            )
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%a").lower()[:3]
            if current_time == target_time and current_day in target_days:
                should_fire = True

        elif trigger_type == "scheduled_weekly":
            target_day = trigger_config.get("day", "monday")
            target_time = trigger_config.get("time", "09:00")
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%A").lower()
            if current_time == target_time and current_day == target_day:
                should_fire = True

        if not should_fire:
            continue
        if _scheduled_rule_already_fired(rule, now):
            continue

        try:
            await execute_automation_rule(rule["id"], None, {"trigger": trigger_type})
            triggered += 1
        except Exception:
            logger.exception(
                "schedule_automation_check: failed to execute rule %s", rule["id"]
            )

    return triggered
