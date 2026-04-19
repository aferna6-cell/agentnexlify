"""Automation rule engine — trigger evaluation and action execution."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import (
    build_unsubscribe_url,
    send_email,
)
from backend.services.sms_rate_limiter import increment_sms_count
from backend.services.task_utils import safe_create_task
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

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


async def execute_automation_rule(
    rule_id: str, lead_id: str | None = None, context: dict | None = None
) -> dict:
    """Execute an automation rule's actions for a given lead.

    Returns a dict with status, actions_run, and error_message.
    """
    db = get_service_supabase()
    context = context or {}
    start_time = datetime.now(timezone.utc)

    try:
        rule_result = (
            db.table("automation_rules")
            .select("*")
            .eq("id", rule_id)
            .limit(1)
            .execute()
        )
        if not rule_result.data:
            return {"status": "failed", "error_message": "Rule not found"}
        rule = rule_result.data[0]
    except Exception as e:
        return {"status": "failed", "error_message": str(e)}

    tenant_id = rule["tenant_id"]
    lead_data = None
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id)
                .select("*")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
            lead_data = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.exception(
                "Failed to load lead %s for automation rule %s", lead_id, rule_id
            )

    actions = rule.get("actions") or []
    actions_run = []
    has_failure = False
    has_partial = False

    for action in actions:
        action_type = action.get("type", "")
        action_config = action.get("config") or {}
        try:
            result = await _execute_action(
                action_type=action_type,
                action_config=action_config,
                lead_data=lead_data,
                tenant_id=tenant_id,
                context=context,
            )
            actions_run.append({"action_type": action_type, "result": result})
            if result.get("status") == "failed":
                has_failure = True
            elif result.get("status") == "partial":
                has_partial = True
        except Exception as e:
            actions_run.append(
                {
                    "action_type": action_type,
                    "result": {"status": "failed", "error": str(e)},
                }
            )
            has_failure = True
            logger.exception("Action %s failed for rule %s", action_type, rule_id)

    end_time = datetime.now(timezone.utc)
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

    if has_failure:
        status = "failed"
    elif has_partial:
        status = "partial"
    else:
        status = "success"

    trigger_event = {
        "trigger_type": rule.get("trigger_type"),
        "trigger_config": rule.get("trigger_config"),
        "lead_id": lead_id,
        "context": context,
    }

    try:
        tenant_table(db, "automation_rule_executions", tenant_id).insert(
            {
                "automation_rule_id": rule_id,
                "tenant_id": tenant_id,
                "trigger_event": trigger_event,
                "actions_run": actions_run,
                "status": status,
                "execution_time_ms": execution_time_ms,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to log automation rule execution for rule %s", rule_id)

    try:
        tenant_table(db, "automation_rules", tenant_id).update(
            {
                "last_triggered_at": end_time.isoformat(),
                "triggered_count": (rule.get("triggered_count") or 0) + 1,
            }
        ).eq("id", rule_id).execute()
    except Exception:
        logger.exception("Failed to update trigger stats for rule %s", rule_id)

    return {
        "status": status,
        "actions_run": actions_run,
        "execution_time_ms": execution_time_ms,
    }


async def _execute_action(
    action_type: str,
    action_config: dict,
    lead_data: dict | None,
    tenant_id: str,
    context: dict,
) -> dict:
    """Execute a single automation action and return result."""
    db = get_service_supabase()

    if action_type == "send_email":
        if not lead_data or not lead_data.get("email"):
            return {"status": "skipped", "reason": "no_email"}
        # CAN-SPAM: never send to unsubscribed leads
        if lead_data.get("unsubscribed"):
            return {"status": "skipped", "reason": "unsubscribed"}
        subject = action_config.get("subject", "")
        body = action_config.get("body", "")
        unsub_url = build_unsubscribe_url(lead_data["id"], tenant_id)
        result = await send_email(
            to=lead_data["email"],
            subject=subject,
            body_html=body,
            tenant_id=tenant_id,
            unsubscribe_url=unsub_url,
            lead_id=lead_data.get("id"),
        )
        return {
            "status": "sent" if result.get("success") else "failed",
            "detail": result,
        }

    elif action_type == "add_tag":
        if not lead_data:
            return {"status": "skipped", "reason": "no_lead"}
        tag = action_config.get("tag", "")
        if not tag:
            return {"status": "failed", "reason": "no_tag"}
        current_tags = set(lead_data.get("tags") or [])
        current_tags.add(tag)
        tenant_table(db, "leads", tenant_id).update({"tags": list(current_tags)}).eq(
            "id", lead_data["id"]
        ).execute()
        return {"status": "success", "tag": tag}

    elif action_type == "remove_tag":
        if not lead_data:
            return {"status": "skipped", "reason": "no_lead"}
        tag = action_config.get("tag", "")
        if not tag:
            return {"status": "failed", "reason": "no_tag"}
        current_tags = set(lead_data.get("tags") or [])
        current_tags.discard(tag)
        tenant_table(db, "leads", tenant_id).update({"tags": list(current_tags)}).eq(
            "id", lead_data["id"]
        ).execute()
        return {"status": "success", "tag": tag}

    elif action_type == "update_lead_status":
        if not lead_data:
            return {"status": "skipped", "reason": "no_lead"}
        new_status = action_config.get("status", "")
        if not new_status:
            return {"status": "failed", "reason": "no_status"}
        tenant_table(db, "leads", tenant_id).update({"status": new_status}).eq(
            "id", lead_data["id"]
        ).execute()
        return {"status": "success", "new_status": new_status}

    elif action_type == "enroll_in_sequence":
        sequence_id = action_config.get("sequence_id")
        if not sequence_id or not lead_data:
            return {"status": "failed", "reason": "missing_sequence_id_or_lead"}
        try:
            sequence_result = (
                tenant_table(db, "automation_sequences", tenant_id)
                .select("id")
                .eq("id", sequence_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if not sequence_result.data:
                return {"status": "failed", "reason": "sequence_not_found"}

            first_step_result = (
                db.table("automation_steps")
                .select("step_order, delay_minutes")
                .eq("sequence_id", sequence_id)
                .eq("is_active", True)
                .order("step_order")
                .limit(1)
                .execute()
            )
            if not first_step_result.data:
                return {"status": "failed", "reason": "sequence_has_no_active_steps"}

            first_step = first_step_result.data[0]
            delay = first_step.get("delay_minutes") or 0
            next_run = datetime.now(timezone.utc) + timedelta(minutes=delay)
            tenant_table(db, "automation_executions", tenant_id).insert(
                {
                    "sequence_id": sequence_id,
                    "lead_id": lead_data["id"],
                    "tenant_id": tenant_id,
                    "current_step": first_step["step_order"],
                    "status": "in_progress",
                    "next_run_at": next_run.isoformat(),
                }
            ).execute()
            return {"status": "success", "sequence_id": sequence_id}
        except Exception:
            return {"status": "failed", "reason": "already_enrolled_or_error"}

    elif action_type == "create_task":
        description = action_config.get("description", "Automation task")
        priority = action_config.get("priority", "medium")
        assigned_to = action_config.get("assigned_to")
        task_payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "description": description,
            "priority": priority,
        }
        if lead_data:
            task_payload["lead_id"] = lead_data["id"]
        if assigned_to:
            task_payload["assigned_to"] = assigned_to
        tenant_table(db, "action_items", tenant_id).insert(task_payload).execute()
        return {"status": "success", "description": description}

    elif action_type == "notify_team":
        message = action_config.get("message", "")
        channel = action_config.get("channel", "dashboard")
        if channel == "sms":
            tenant_result = (
                tenant_table(db, "tenants", tenant_id)
                .select("notification_phone")
                .limit(1)
                .execute()
            )
            phone = (
                tenant_result.data[0].get("notification_phone")
                if tenant_result.data
                else None
            )
            if phone:
                sms_ok = await send_sms(to=phone, body=message)
                return {"status": "sent" if sms_ok else "failed"}
        return {"status": "success", "message": message}

    elif action_type == "send_campaign":
        campaign_id = action_config.get("campaign_id")
        if not campaign_id:
            return {"status": "failed", "reason": "no_campaign_id"}
        safe_create_task(_send_campaign_for_rule(campaign_id, tenant_id, lead_data), name="campaign_for_rule")
        return {"status": "dispatched", "campaign_id": campaign_id}

    elif action_type == "update_lead_score":
        if not lead_data:
            return {"status": "skipped", "reason": "no_lead"}
        delta = action_config.get("delta", 0)
        current_score = float(lead_data.get("lead_score") or 0)
        new_score = current_score + delta
        tenant_table(db, "leads", tenant_id).update({"lead_score": new_score}).eq(
            "id", lead_data["id"]
        ).execute()
        return {"status": "success", "new_score": new_score}

    else:
        return {"status": "failed", "reason": f"unknown_action_type: {action_type}"}


async def _send_campaign_for_rule(
    campaign_id: str, tenant_id: str, lead_data: dict | None
) -> None:
    """Background task to send a campaign to a specific lead (from automation rule)."""
    if not lead_data:
        return
    try:
        from backend.services.campaign_service import _send_campaign_background

        db = get_service_supabase()
        campaign_result = (
            tenant_table(db, "marketing_campaigns", tenant_id)
            .select("*")
            .eq("id", campaign_id)
            .limit(1)
            .execute()
        )
        if not campaign_result.data:
            return
        campaign = campaign_result.data[0]
        await _send_campaign_background(campaign_id, tenant_id, [lead_data], campaign)
    except Exception:
        logger.exception("Failed to send campaign %s for rule automation", campaign_id)


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
