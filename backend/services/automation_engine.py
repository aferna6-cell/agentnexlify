"""Automation engine — triggers, processes, and executes email sequences."""


import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_supabase
from backend.services.email_sender import build_branded_email_html, render_sms_template, render_template, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50


async def trigger_sequence(
    tenant_id: str,
    lead_id: str,
    trigger_event: str,
    trigger_context: dict[str, Any] | None = None,
) -> int:
    """Find matching active sequences and enroll the lead. Returns count of enrollments created."""
    db = get_supabase()
    trigger_context = trigger_context or {}

    # Find active sequences for this trigger event
    result = (
        db.table("automation_sequences")
        .select("id, trigger_config")
        .eq("tenant_id", tenant_id)
        .eq("trigger_event", trigger_event)
        .eq("is_active", True)
        .execute()
    )

    enrolled = 0
    for seq in result.data or []:
        # For lead_stage_change, check target_stage matches
        if trigger_event == "lead_stage_change":
            target = (seq.get("trigger_config") or {}).get("target_stage")
            if target and target != trigger_context.get("new_stage"):
                continue

        # Get the first step's delay
        steps = (
            db.table("automation_steps")
            .select("delay_minutes")
            .eq("sequence_id", seq["id"])
            .eq("is_active", True)
            .order("step_order")
            .limit(1)
            .execute()
        )
        if not steps.data:
            continue

        delay = steps.data[0]["delay_minutes"]
        next_run = datetime.now(timezone.utc) + timedelta(minutes=delay)

        try:
            db.table("automation_executions").insert({
                "sequence_id": seq["id"],
                "lead_id": lead_id,
                "tenant_id": tenant_id,
                "current_step": 1,
                "status": "in_progress",
                "next_run_at": next_run.isoformat(),
            }).execute()
            enrolled += 1
            logger.info(
                "Enrolled lead %s in sequence %s (trigger: %s)",
                lead_id, seq["id"], trigger_event,
            )
        except Exception:
            # UNIQUE constraint violation means already enrolled — skip
            logger.debug("Lead %s already enrolled in sequence %s", lead_id, seq["id"])

    return enrolled


async def process_pending_steps() -> int:
    """Process all pending automation steps that are due. Returns count processed."""
    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # Find executions that are due
    result = (
        db.table("automation_executions")
        .select("id")
        .eq("status", "in_progress")
        .lte("next_run_at", now)
        .limit(BATCH_LIMIT)
        .execute()
    )

    processed = 0
    for exec_row in result.data or []:
        try:
            await execute_step(exec_row["id"])
            processed += 1
        except Exception:
            logger.exception("Failed to execute step for execution %s", exec_row["id"])

    return processed


async def execute_step(execution_id: str) -> None:
    """Execute the current step of an automation execution."""
    db = get_supabase()

    # Load execution
    exec_result = (
        db.table("automation_executions")
        .select("*")
        .eq("id", execution_id)
        .limit(1)
        .execute()
    )
    if not exec_result.data:
        return
    execution = exec_result.data[0]

    # Load the current step
    steps_result = (
        db.table("automation_steps")
        .select("*")
        .eq("sequence_id", execution["sequence_id"])
        .eq("step_order", execution["current_step"])
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not steps_result.data:
        # No active step at this order — mark completed
        db.table("automation_executions").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", execution_id).execute()
        return
    step = steps_result.data[0]

    # Load lead
    lead_result = (
        db.table("leads")
        .select("id, name, email, phone")
        .eq("id", execution["lead_id"])
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        db.table("automation_executions").update({
            "status": "failed",
        }).eq("id", execution_id).execute()
        return
    lead = lead_result.data[0]

    # Load tenant for business_name and plan
    tenant_result = (
        db.table("tenants")
        .select("id, business_name, plan")
        .eq("id", execution["tenant_id"])
        .limit(1)
        .execute()
    )
    tenant = tenant_result.data[0] if tenant_result.data else {}

    # Build template context
    context = {
        "name": lead.get("name") or "there",
        "email": lead.get("email") or "",
        "phone": lead.get("phone") or "",
        "business_name": tenant.get("business_name") or "Our Team",
    }

    action_type = step.get("action_type", "email")

    if action_type == "sms":
        # --- SMS path ---
        if not lead.get("phone"):
            db.table("automation_logs").insert({
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": "skipped",
                "details": {"reason": "no_phone"},
            }).execute()
            _advance_execution(db, execution, step)
            return

        plan = tenant.get("plan", "free")
        if not check_sms_rate_limit(execution["tenant_id"], plan):
            db.table("automation_logs").insert({
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": "skipped",
                "details": {"reason": "sms_rate_limit"},
            }).execute()
            _advance_execution(db, execution, step)
            return

        body = render_sms_template(step["body_template"], context)
        sms_ok = await send_sms(to=lead["phone"], body=body)

        action = "sms_sent" if sms_ok else "sms_failed"
        db.table("automation_logs").insert({
            "execution_id": execution_id,
            "step_id": step["id"],
            "action": action,
            "details": {"phone": lead["phone"]},
        }).execute()

        if sms_ok:
            increment_sms_count(execution["tenant_id"])
            fire_event_background(execution["tenant_id"], "automation.sms_sent", {
                "lead_id": execution["lead_id"],
                "lead_phone": lead["phone"],
                "sequence_id": execution["sequence_id"],
                "step_order": execution["current_step"],
            })
        else:
            logger.warning(
                "SMS failed for execution %s step %s",
                execution_id, step["id"],
            )
    else:
        # --- Email path (default) ---
        if not lead.get("email"):
            db.table("automation_logs").insert({
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": "skipped",
                "details": {"reason": "no_email"},
            }).execute()
            _advance_execution(db, execution, step)
            return

        subject = render_template(step["subject_template"], context)
        body = render_template(step["body_template"], context)

        # Branded email wrapping for Operations/Enterprise plans
        plan = tenant.get("plan", "free")
        if plan in ("professional", "enterprise"):
            try:
                wc_result = (
                    db.table("widget_configs")
                    .select("branding")
                    .eq("tenant_id", execution["tenant_id"])
                    .limit(1)
                    .execute()
                )
                wc_branding = (wc_result.data[0].get("branding") or {}) if wc_result.data else {}
                if wc_branding:
                    body = build_branded_email_html(body, wc_branding, tenant.get("business_name", ""))
            except Exception:
                logger.debug("Failed to load branding for email, sending plain", exc_info=True)

        result = await send_email(
            to=lead["email"],
            subject=subject,
            body_html=body,
            tenant_id=execution["tenant_id"],
        )

        action = "email_sent" if result["success"] else "email_failed"
        db.table("automation_logs").insert({
            "execution_id": execution_id,
            "step_id": step["id"],
            "action": action,
            "details": result,
        }).execute()

        if result["success"]:
            fire_event_background(execution["tenant_id"], "automation.email_sent", {
                "lead_id": execution["lead_id"],
                "lead_email": lead["email"],
                "subject": subject,
                "sequence_id": execution["sequence_id"],
                "step_order": execution["current_step"],
            })

        if not result["success"]:
            logger.warning(
                "Email failed for execution %s step %s: %s",
                execution_id, step["id"], result.get("detail"),
            )

    _advance_execution(db, execution, step)


def _advance_execution(db, execution: dict, current_step: dict) -> None:
    """Move execution to next step or mark completed."""
    # Check if there's a next step
    next_steps = (
        db.table("automation_steps")
        .select("step_order, delay_minutes")
        .eq("sequence_id", execution["sequence_id"])
        .gt("step_order", execution["current_step"])
        .eq("is_active", True)
        .order("step_order")
        .limit(1)
        .execute()
    )

    if next_steps.data:
        next_step = next_steps.data[0]
        next_run = datetime.now(timezone.utc) + timedelta(minutes=next_step["delay_minutes"])
        db.table("automation_executions").update({
            "current_step": next_step["step_order"],
            "next_run_at": next_run.isoformat(),
        }).eq("id", execution["id"]).execute()
    else:
        db.table("automation_executions").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", execution["id"]).execute()


async def check_no_response_leads() -> int:
    """Find leads with no response in 24h and trigger sequences. Returns count triggered.

    DISABLED: The live conversations table schema doesn't reliably have the
    columns needed for this query (started_at, last_message_at, and even
    created_at filters return HTTP 400).  Re-enable once the conversations
    schema is verified / migrated.
    """
    logger.debug("check_no_response_leads: skipped (disabled — conversations schema mismatch)")
    return 0
