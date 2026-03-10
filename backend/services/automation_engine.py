"""Automation engine — triggers, processes, and executes email sequences."""


import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from backend.models.database import get_supabase
from backend.services.email_sender import build_branded_email_html, render_sms_template, render_template, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50

VALID_TRIGGER_EVENTS = {"new_lead", "lead_stage_change", "no_response_24h", "appointment_completed"}


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

    # Load tenant for business_name, plan, and google_review_link
    tenant_result = (
        db.table("tenants")
        .select("id, business_name, plan, google_review_link")
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
        "review_link": tenant.get("google_review_link") or "",
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
    elif action_type == "ai_email":
        # --- AI Email path ---
        if not lead.get("email"):
            db.table("automation_logs").insert({
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": "skipped",
                "details": {"reason": "no_email"},
            }).execute()
            _advance_execution(db, execution, step)
            return

        ai_body = await _generate_ai_email(
            db, execution["tenant_id"], execution["lead_id"],
            tenant.get("business_name", ""), step.get("body_template"),
        )

        subject = render_template(step["subject_template"], context)

        # Branded wrapping
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
                    ai_body = build_branded_email_html(ai_body, wc_branding, tenant.get("business_name", ""))
            except Exception:
                logger.debug("Failed to load branding for AI email, sending plain", exc_info=True)

        result = await send_email(
            to=lead["email"],
            subject=subject,
            body_html=ai_body,
            tenant_id=execution["tenant_id"],
        )

        action = "ai_email_sent" if result["success"] else "ai_email_failed"
        db.table("automation_logs").insert({
            "execution_id": execution_id,
            "step_id": step["id"],
            "action": action,
            "details": {**result, "ai_generated_body": ai_body[:500]},
        }).execute()

        if result["success"]:
            fire_event_background(execution["tenant_id"], "automation.email_sent", {
                "lead_id": execution["lead_id"],
                "lead_email": lead["email"],
                "subject": subject,
                "sequence_id": execution["sequence_id"],
                "step_order": execution["current_step"],
                "ai_generated": True,
            })
        else:
            logger.warning(
                "AI email failed for execution %s step %s: %s",
                execution_id, step["id"], result.get("detail"),
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


async def _generate_ai_email(
    db, tenant_id: str, lead_id: str, business_name: str, body_template: str | None
) -> str:
    """Generate a personalized email body using Anthropic API."""
    import anthropic
    from backend.config import settings as app_settings

    # Load recent conversation history for this lead
    conv_result = (
        db.table("chat_messages")
        .select("role, content")
        .eq("tenant_id", tenant_id)
        .eq("lead_id", lead_id)
        .order("created_at", desc=False)
        .limit(20)
        .execute()
    )
    conversation = conv_result.data or []
    conv_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in conversation
    ) if conversation else "No conversation history available."

    # Load FAQ entries for context
    faq_result = (
        db.table("faq_entries")
        .select("question, answer")
        .eq("tenant_id", tenant_id)
        .limit(20)
        .execute()
    )
    faq_text = "\n".join(
        f"Q: {f['question']}\nA: {f['answer']}" for f in (faq_result.data or [])
    ) if faq_result.data else "No FAQ entries available."

    system_prompt = (
        f"You are a helpful assistant for {business_name}. "
        "Based on this customer's conversation and our FAQ, draft a personalized follow-up email. "
        "Keep it friendly, short (3-4 sentences), and helpful. "
        "Return ONLY the email body HTML (no subject line). Use <p> tags for paragraphs."
    )

    user_content = f"Customer conversation:\n{conv_text}\n\nBusiness FAQ:\n{faq_text}"
    if body_template and body_template.strip():
        user_content += f"\n\nUse this as a guide/template to enhance:\n{body_template}"

    try:
        # Run sync Anthropic call in thread pool to avoid blocking the event loop
        client = anthropic.Anthropic(api_key=app_settings.anthropic_api_key)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                client.messages.create,
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            ),
        )
        return response.content[0].text
    except Exception:
        logger.exception("AI email generation failed for tenant %s, lead %s", tenant_id, lead_id)
        # Fallback: use the body_template if provided, else a generic message
        if body_template and body_template.strip():
            return body_template
        return (
            f"<p>Hi there,</p>"
            f"<p>Thank you for connecting with {business_name}! "
            f"We wanted to follow up and see if there's anything else we can help you with.</p>"
            f"<p>Best regards,<br>The {business_name} Team</p>"
        )


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
