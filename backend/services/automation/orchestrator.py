"""Automation orchestrator — step processing and execution."""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import (
    build_branded_email_html,
    build_unsubscribe_url,
    render_sms_template,
    render_template,
    send_email,
)
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background
from backend.services.automation.trigger import BATCH_LIMIT

logger = logging.getLogger(__name__)


async def process_pending_steps() -> int:
    """Process all pending automation steps that are due. Returns count processed."""
    db = get_service_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # Batch-fetch all pending execution rows in a single query (select * to avoid re-fetch)
    result = (
        db.table("automation_executions")
        .select("*")
        .eq("status", "in_progress")
        .lte("next_run_at", now)
        .limit(BATCH_LIMIT)
        .execute()
    )

    # Build dict keyed by execution ID so execute_step can skip the DB re-fetch
    execution_data_by_id: dict = {row["id"]: row for row in (result.data or [])}

    processed = 0
    for execution_id, execution_data in execution_data_by_id.items():
        try:
            await execute_step(execution_id, execution_data=execution_data)
            processed += 1
        except Exception:
            logger.exception("Failed to execute step for execution %s", execution_id)

    return processed


async def execute_step(execution_id: str, execution_data: dict | None = None) -> None:
    """Execute the current step of an automation execution.

    Args:
        execution_id: Primary key of the automation_executions row.
        execution_data: Pre-loaded execution row dict. When provided (batch callers),
            the DB re-fetch is skipped. When None (direct callers), the row is fetched
            from the database as before.
    """
    db = get_service_supabase()

    # Use pre-loaded data if available; otherwise fetch from DB (single-call path)
    if execution_data is not None:
        execution = execution_data
    else:
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
        tenant_table(db, "automation_executions", execution["tenant_id"]).update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", execution_id).execute()
        return
    step = steps_result.data[0]

    # Load lead
    lead_result = (
        tenant_table(db, "leads", execution["tenant_id"])
        .select("id, name, email, phone, unsubscribed")
        .eq("id", execution["lead_id"])
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        tenant_table(db, "automation_executions", execution["tenant_id"]).update(
            {
                "status": "failed",
            }
        ).eq("id", execution_id).execute()
        return
    lead = lead_result.data[0]

    # CAN-SPAM: skip unsubscribed leads
    if lead.get("unsubscribed"):
        db.table("automation_logs").insert(
            {
                "execution_id": execution_id,
                "step_id": step["id"] if steps_result.data else None,
                "action": "skipped",
                "details": {"reason": "unsubscribed"},
            }
        ).execute()
        tenant_table(db, "automation_executions", execution["tenant_id"]).update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", execution_id).execute()
        return

    # Load tenant for business_name, plan, and google_review_link
    tenant_result = (
        tenant_table(db, "tenants", execution["tenant_id"])
        .select("id, business_name, plan, google_review_link")
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
            db.table("automation_logs").insert(
                {
                    "execution_id": execution_id,
                    "step_id": step["id"],
                    "action": "skipped",
                    "details": {"reason": "no_phone"},
                }
            ).execute()
            _advance_execution(db, execution, step)
            return

        plan = tenant.get("plan") or "free"
        if not check_sms_rate_limit(execution["tenant_id"], plan):
            db.table("automation_logs").insert(
                {
                    "execution_id": execution_id,
                    "step_id": step["id"],
                    "action": "skipped",
                    "details": {"reason": "sms_rate_limit"},
                }
            ).execute()
            _advance_execution(db, execution, step)
            return

        body = render_sms_template(step["body_template"], context)
        sms_ok = await send_sms(to=lead["phone"], body=body)

        action = "sms_sent" if sms_ok else "sms_failed"
        db.table("automation_logs").insert(
            {
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": action,
                "details": {"phone": lead["phone"]},
            }
        ).execute()

        if sms_ok:
            increment_sms_count(execution["tenant_id"])
            fire_event_background(
                execution["tenant_id"],
                "automation.sms_sent",
                {
                    "lead_id": execution["lead_id"],
                    "lead_phone": lead["phone"],
                    "sequence_id": execution["sequence_id"],
                    "step_order": execution["current_step"],
                },
            )
        else:
            logger.warning(
                "SMS failed for execution %s step %s",
                execution_id,
                step["id"],
            )
    elif action_type == "ai_email":
        # --- AI Email path ---
        if not lead.get("email"):
            db.table("automation_logs").insert(
                {
                    "execution_id": execution_id,
                    "step_id": step["id"],
                    "action": "skipped",
                    "details": {"reason": "no_email"},
                }
            ).execute()
            _advance_execution(db, execution, step)
            return

        ai_body = await _generate_ai_email(
            db,
            execution["tenant_id"],
            execution["lead_id"],
            tenant.get("business_name") or "",
            step.get("body_template"),
        )

        subject = render_template(step["subject_template"], context)

        # Branded wrapping
        plan = tenant.get("plan") or "free"
        if plan in ("professional", "enterprise"):
            try:
                wc_result = (
                    db.table("widget_configs")
                    .select("branding")
                    .eq("tenant_id", execution["tenant_id"])
                    .limit(1)
                    .execute()
                )
                wc_branding = (
                    (wc_result.data[0].get("branding") or {}) if wc_result.data else {}
                )
                if wc_branding:
                    ai_body = build_branded_email_html(
                        ai_body, wc_branding, tenant.get("business_name") or ""
                    )
            except Exception:
                logger.debug(
                    "Failed to load branding for AI email, sending plain", exc_info=True
                )

        unsub_url = build_unsubscribe_url(lead["id"], execution["tenant_id"])
        result = await send_email(
            to=lead["email"],
            subject=subject,
            body_html=ai_body,
            tenant_id=execution["tenant_id"],
            unsubscribe_url=unsub_url,
            lead_id=lead["id"],
            execution_id=execution_id,
        )

        action = "ai_email_sent" if result["success"] else "ai_email_failed"
        db.table("automation_logs").insert(
            {
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": action,
                "details": {**result, "ai_generated_body": ai_body[:500]},
            }
        ).execute()

        if result["success"]:
            fire_event_background(
                execution["tenant_id"],
                "automation.email_sent",
                {
                    "lead_id": execution["lead_id"],
                    "lead_email": lead["email"],
                    "subject": subject,
                    "sequence_id": execution["sequence_id"],
                    "step_order": execution["current_step"],
                    "ai_generated": True,
                },
            )
        else:
            logger.warning(
                "AI email failed for execution %s step %s: %s",
                execution_id,
                step["id"],
                result.get("detail"),
            )
    else:
        # --- Email path (default) ---
        if not lead.get("email"):
            db.table("automation_logs").insert(
                {
                    "execution_id": execution_id,
                    "step_id": step["id"],
                    "action": "skipped",
                    "details": {"reason": "no_email"},
                }
            ).execute()
            _advance_execution(db, execution, step)
            return

        subject = render_template(step["subject_template"], context)
        body = render_template(step["body_template"], context)

        # Branded email wrapping for Professional/Enterprise plans
        plan = tenant.get("plan") or "free"
        if plan in ("professional", "enterprise"):
            try:
                wc_result = (
                    db.table("widget_configs")
                    .select("branding")
                    .eq("tenant_id", execution["tenant_id"])
                    .limit(1)
                    .execute()
                )
                wc_branding = (
                    (wc_result.data[0].get("branding") or {}) if wc_result.data else {}
                )
                if wc_branding:
                    body = build_branded_email_html(
                        body, wc_branding, tenant.get("business_name") or ""
                    )
            except Exception:
                logger.debug(
                    "Failed to load branding for email, sending plain", exc_info=True
                )

        unsub_url = build_unsubscribe_url(lead["id"], execution["tenant_id"])
        result = await send_email(
            to=lead["email"],
            subject=subject,
            body_html=body,
            tenant_id=execution["tenant_id"],
            unsubscribe_url=unsub_url,
            lead_id=lead["id"],
            execution_id=execution_id,
        )

        action = "email_sent" if result["success"] else "email_failed"
        db.table("automation_logs").insert(
            {
                "execution_id": execution_id,
                "step_id": step["id"],
                "action": action,
                "details": result,
            }
        ).execute()

        if result["success"]:
            fire_event_background(
                execution["tenant_id"],
                "automation.email_sent",
                {
                    "lead_id": execution["lead_id"],
                    "lead_email": lead["email"],
                    "subject": subject,
                    "sequence_id": execution["sequence_id"],
                    "step_order": execution["current_step"],
                },
            )

        if not result["success"]:
            logger.warning(
                "Email failed for execution %s step %s: %s",
                execution_id,
                step["id"],
                result.get("detail"),
            )

    _advance_execution(db, execution, step)


async def _generate_ai_email(
    db, tenant_id: str, lead_id: str, business_name: str, body_template: str | None
) -> str:
    """Generate a personalized email body using the shared Claude runtime."""
    from backend.services.llm_runtime import call_claude_messages

    # Load recent conversation history for this lead.
    # Path: leads.conversation_id → conversations.session_id → chat_messages
    conversation = []
    try:
        lead_row = (
            tenant_table(db, "leads", tenant_id)
            .select("conversation_id")
            .eq("id", lead_id)
            .limit(1)
            .execute()
        )
        conv_id = lead_row.data[0].get("conversation_id") if lead_row.data else None
        session_id = None
        if conv_id:
            conv_row = (
                tenant_table(db, "conversations", tenant_id)
                .select("session_id")
                .eq("id", conv_id)
                .limit(1)
                .execute()
            )
            session_id = conv_row.data[0].get("session_id") if conv_row.data else None
        if session_id:
            msg_result = (
                tenant_table(db, "chat_messages", tenant_id)
                .select("role, content")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .limit(20)
                .execute()
            )
            conversation = msg_result.data or []
    except Exception:
        logger.warning(
            "Failed to load conversation context for lead %s", lead_id, exc_info=True
        )

    conv_text = (
        "\n".join(f"{m['role']}: {m['content']}" for m in conversation)
        if conversation
        else "No conversation history available."
    )

    # Load FAQ entries for context
    faq_result = (
        tenant_table(db, "faq_entries", tenant_id)
        .select("question, answer")
        .limit(20)
        .execute()
    )
    faq_text = (
        "\n".join(
            f"Q: {f['question']}\nA: {f['answer']}" for f in (faq_result.data or [])
        )
        if faq_result.data
        else "No FAQ entries available."
    )

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
        response = await call_claude_messages(
            operation="automation.generate_ai_email",
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            timeout=30.0,
            max_retries=1,
            retry_delay_seconds=0.75,
            metadata={
                "tenant_id": tenant_id,
                "lead_id": lead_id,
                "business_name": business_name,
                "has_template": bool(body_template and body_template.strip()),
                "conversation_messages": len(conversation),
                "faq_count": len(faq_result.data or []),
            },
        )
        return response.text
    except Exception:
        logger.exception(
            "AI email generation failed for tenant %s, lead %s", tenant_id, lead_id
        )
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
        next_run = datetime.now(timezone.utc) + timedelta(
            minutes=next_step["delay_minutes"]
        )
        db.table("automation_executions").update(
            {
                "current_step": next_step["step_order"],
                "next_run_at": next_run.isoformat(),
            }
        ).eq("id", execution["id"]).execute()
    else:
        db.table("automation_executions").update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", execution["id"]).execute()
