"""Automation rule engine — execute rules and dispatch actions.

Trigger evaluation lives in `triggers.py`. Domain-event dispatch
(`check_lead_captured_triggers`, etc.) lives in `trigger_dispatch.py`.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import (
    build_unsubscribe_url,
    send_email,
)
from backend.services.task_utils import safe_create_task
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


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
