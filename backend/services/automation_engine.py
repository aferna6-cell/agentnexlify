"""Automation engine — triggers, processes, and executes email sequences."""


import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from backend.models.database import get_supabase
from backend.services.email_sender import build_branded_email_html, build_unsubscribe_url, render_sms_template, render_template, send_email
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
        .select("id, name, email, phone, unsubscribed")
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

    # CAN-SPAM: skip unsubscribed leads
    if lead.get("unsubscribed"):
        db.table("automation_logs").insert({
            "execution_id": execution_id,
            "step_id": step["id"] if steps_result.data else None,
            "action": "skipped",
            "details": {"reason": "unsubscribed"},
        }).execute()
        db.table("automation_executions").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", execution_id).execute()
        return

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

        unsub_url = build_unsubscribe_url(lead["id"])
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

        # Branded email wrapping for Professional/Enterprise plans
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

        unsub_url = build_unsubscribe_url(lead["id"])
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

    # Load recent conversation history for this lead.
    # Path: leads.conversation_id → conversations.session_id → chat_messages
    conversation = []
    try:
        lead_row = (
            db.table("leads")
            .select("conversation_id")
            .eq("id", lead_id)
            .limit(1)
            .execute()
        )
        conv_id = (lead_row.data[0].get("conversation_id") if lead_row.data else None)
        session_id = None
        if conv_id:
            conv_row = (
                db.table("conversations")
                .select("session_id")
                .eq("id", conv_id)
                .limit(1)
                .execute()
            )
            session_id = (conv_row.data[0].get("session_id") if conv_row.data else None)
        if session_id:
            msg_result = (
                db.table("chat_messages")
                .select("role, content")
                .eq("tenant_id", tenant_id)
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .limit(20)
                .execute()
            )
            conversation = msg_result.data or []
    except Exception:
        logger.warning("Failed to load conversation context for lead %s", lead_id, exc_info=True)

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
        client = anthropic.Anthropic(api_key=app_settings.anthropic_api_key, timeout=30.0)
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            partial(
                client.messages.create,
                model="claude-sonnet-4-6",
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


async def send_appointment_reminders() -> int:
    """Check for upcoming appointments and send email/SMS reminders.

    Sends reminders at two windows:
    - 24 hours before (23h-25h window)
    - 1 hour before (30m-90m window)

    Uses a simple approach: query appointments in each window that haven't
    had a reminder sent yet (tracked via notes field with reminder tags).
    Returns count of reminders sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    reminder_windows = [
        {"label": "24h", "min_hours": 23, "max_hours": 25},
        {"label": "1h", "min_hours": 0.5, "max_hours": 1.5},
    ]

    for window in reminder_windows:
        window_start = now + timedelta(hours=window["min_hours"])
        window_end = now + timedelta(hours=window["max_hours"])

        try:
            appointments = (
                db.table("appointments")
                .select("id, tenant_id, customer_name, customer_email, customer_phone, start_time, end_time, notes, status")
                .gte("start_time", window_start.isoformat())
                .lte("start_time", window_end.isoformat())
                .eq("status", "booked")
                .execute()
            )
        except Exception:
            logger.exception("send_appointment_reminders: failed to query appointments for %s window", window["label"])
            continue

        for appt in appointments.data or []:
            reminder_tag = f"reminder_{window['label']}_sent"
            notes = appt.get("notes") or ""
            if reminder_tag in notes:
                continue

            tenant_id = appt["tenant_id"]

            try:
                tenant = db.table("tenants").select("business_name, owner_email, plan").eq("id", tenant_id).limit(1).execute()
                if not tenant.data:
                    continue
                tenant_data = tenant.data[0]
                business_name = tenant_data.get("business_name") or "Our Team"
            except Exception:
                logger.exception("send_appointment_reminders: failed to load tenant %s", tenant_id)
                continue

            # Format the appointment time nicely
            try:
                start_dt = datetime.fromisoformat(appt["start_time"].replace("Z", "+00:00"))
                time_str = start_dt.strftime("%B %d at %I:%M %p")
            except Exception:
                time_str = appt["start_time"]

            customer_name = appt.get("customer_name") or "there"
            customer_email = appt.get("customer_email")

            # Send email reminder
            if customer_email:
                subject_map = {
                    "24h": f"Reminder: Your appointment with {business_name} tomorrow",
                    "1h": f"Your appointment with {business_name} is in 1 hour",
                }
                body_map = {
                    "24h": (
                        f"<h2>Hi {customer_name},</h2>"
                        f"<p>This is a friendly reminder that you have an appointment "
                        f"with <strong>{business_name}</strong> scheduled for <strong>{time_str}</strong>.</p>"
                        f"<p>If you need to reschedule or cancel, please reply to this email "
                        f"or contact us directly.</p>"
                        f"<p>We look forward to seeing you!</p>"
                        f"<p>Best,<br>The {business_name} Team</p>"
                    ),
                    "1h": (
                        f"<h2>Hi {customer_name},</h2>"
                        f"<p>Just a quick reminder &mdash; your appointment with "
                        f"<strong>{business_name}</strong> is coming up in about 1 hour "
                        f"(<strong>{time_str}</strong>).</p>"
                        f"<p>See you soon!</p>"
                        f"<p>Best,<br>The {business_name} Team</p>"
                    ),
                }

                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        partial(
                            send_email,
                            to=customer_email,
                            subject=subject_map[window["label"]],
                            body_html=body_map[window["label"]],
                            tenant_id=tenant_id,
                        ),
                    )
                    sent += 1
                    logger.info(
                        "Sent %s reminder for appointment %s to %s",
                        window["label"], appt["id"], customer_email,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send %s reminder for appointment %s",
                        window["label"], appt["id"],
                    )

            # Send SMS reminder if phone available
            customer_phone = appt.get("customer_phone")
            if customer_phone:
                sms_map = {
                    "24h": (
                        f"Hi {customer_name}, reminder: you have an appointment "
                        f"with {business_name} tomorrow ({time_str}). "
                        f"Reply to reschedule."
                    ),
                    "1h": (
                        f"Hi {customer_name}, your appointment with "
                        f"{business_name} is in 1 hour ({time_str}). See you soon!"
                    ),
                }
                try:
                    if check_sms_rate_limit(tenant_id, tenant_data.get("plan", "free")):
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            partial(send_sms, to=customer_phone, body=sms_map[window["label"]]),
                        )
                        increment_sms_count(tenant_id)
                        sent += 1
                except Exception:
                    logger.exception(
                        "Failed to send SMS %s reminder for appointment %s",
                        window["label"], appt["id"],
                    )

            # Mark reminder as sent in notes
            updated_notes = f"{notes}\n{reminder_tag}".strip() if notes else reminder_tag
            try:
                db.table("appointments").update({"notes": updated_notes}).eq("id", appt["id"]).execute()
            except Exception:
                logger.exception("Failed to mark reminder sent for appointment %s", appt["id"])

    return sent


async def send_pending_review_requests() -> int:
    """Check for completed appointments that need review requests sent.

    Queries appointments with status='completed' where review_request_sent_at
    is null and the tenant has review requests enabled. Respects the configured
    delay (hours since completion). Sends via email, SMS, or both.

    Returns count of review requests sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    try:
        # Get completed appointments that haven't had review requests sent
        appts = (
            db.table("appointments")
            .select("id, tenant_id, customer_name, customer_email, customer_phone, updated_at, lead_id")
            .eq("status", "completed")
            .is_("review_request_sent_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_pending_review_requests: failed to query appointments")
        return 0

    # Group by tenant to avoid repeated tenant lookups
    tenant_cache: dict[str, dict] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]

        # Load tenant config (cached per tenant)
        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, google_review_link, review_request_config, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.exception("send_pending_review_requests: failed to load tenant %s", tenant_id)
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        config = tenant.get("review_request_config") or {}
        if not config.get("enabled"):
            continue

        review_link = tenant.get("google_review_link") or ""
        if not review_link:
            continue

        # Check delay
        delay_hours = config.get("delay_hours", 24)
        try:
            completed_at = datetime.fromisoformat(
                appt["updated_at"].replace("Z", "+00:00")
            )
        except Exception:
            continue

        if (now - completed_at).total_seconds() < delay_hours * 3600:
            continue

        business_name = tenant.get("business_name") or "Our Team"
        customer_name = appt.get("customer_name") or "there"
        method = config.get("method", "email")

        # CAN-SPAM: skip if lead has unsubscribed
        lead_id = appt.get("lead_id")
        if lead_id:
            try:
                lr = db.table("leads").select("unsubscribed").eq("id", lead_id).limit(1).execute()
                if lr.data and lr.data[0].get("unsubscribed"):
                    continue
            except Exception:
                pass  # If we can't check, proceed (fail-open for review requests)

        # Send email review request
        if method in ("email", "both") and appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id) if lead_id else ""
            subject = f"How was your experience with {business_name}?"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>Thank you for your recent visit with <strong>{business_name}</strong>! "
                f"We hope everything went well.</p>"
                f"<p>We'd really appreciate it if you could take a moment to share your experience:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;font-weight:600;">Leave a Review</a></p>'
                f"<p>Your feedback helps us improve and helps others find us. Thank you!</p>"
                f"<p>Best,<br>The {business_name} Team</p>"
            )
            try:
                result = await send_email(
                    to=appt["customer_email"],
                    subject=subject,
                    body_html=body,
                    tenant_id=tenant_id,
                    unsubscribe_url=unsub_url,
                )
                if result.get("success"):
                    sent += 1
                    logger.info("Sent review request email for appointment %s", appt["id"])
            except Exception:
                logger.exception("Failed to send review request email for appointment %s", appt["id"])

        # Send SMS review request
        if method in ("sms", "both") and appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, thanks for visiting {business_name}! "
                f"We'd love your feedback. Leave a review here: {review_link}"
            )
            try:
                plan = tenant.get("plan", "free")
                if check_sms_rate_limit(tenant_id, plan):
                    sms_ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if sms_ok:
                        increment_sms_count(tenant_id)
                        sent += 1
                        logger.info("Sent review request SMS for appointment %s", appt["id"])
            except Exception:
                logger.exception("Failed to send review request SMS for appointment %s", appt["id"])

        # Mark as sent regardless of success to avoid retry loops
        try:
            db.table("appointments").update({
                "review_request_sent_at": now.isoformat(),
            }).eq("id", appt["id"]).execute()
        except Exception:
            logger.exception("Failed to mark review request sent for appointment %s", appt["id"])

    return sent


# --- Onboarding Email Drip Sequence ---

_ONBOARDING_STEPS = [
    {
        "day": 1,
        "min_hours": 23,
        "max_hours": 26,
        "subject": "Quick win: teach your AI about {{business_name}}",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>Your chat widget is ready to go. Now let's make it sound like <em>you</em>.</p>"
            "<p><strong>The fastest way to improve your AI: add your top 5 FAQs.</strong></p>"
            "<p>Go to your <a href='https://agentnexlify.vercel.app'>FAQ Manager</a> and add the "
            "questions your customers ask the most: your hours, pricing, service area, what makes "
            "you different, and how to book.</p>"
            "<p>Each FAQ you add makes the AI smarter. Customers get instant, accurate answers "
            "instead of &ldquo;I'm not sure.&rdquo;</p>"
            "<p><strong>Bonus:</strong> If you have a website, go to Settings and paste your URL. "
            "Click &ldquo;Scan Website&rdquo; &mdash; the AI will read your site and learn your "
            "services automatically.</p>"
            "<p><a href='https://agentnexlify.vercel.app' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Open your dashboard &rarr;</a></p>"
            "<p>Talk soon,<br>The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 3,
        "min_hours": 71,
        "max_hours": 74,
        "subject": "Your AI had its first conversations — here's what happened",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>By now your AI assistant has probably had a few conversations with visitors.</p>"
            "<p><strong>See every conversation:</strong> Go to "
            "<a href='https://agentnexlify.vercel.app'>Conversations</a> to see what visitors "
            "asked and how the AI responded.</p>"
            "<p><strong>Improve the AI with one click:</strong> See a response you don't love? "
            "Click the thumbs-down button and type what the AI <em>should</em> have said. "
            "It learns from your corrections.</p>"
            "<p><strong>Check your leads:</strong> Go to Leads to see everyone who shared their "
            "contact info. Follow up within an hour for the best results.</p>"
            "<p><a href='https://agentnexlify.vercel.app' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Check your conversations &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 7,
        "min_hours": 167,
        "max_hours": 170,
        "subject": "One week in — are you capturing every lead?",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>It's been a week since you set up your AI assistant for {{business_name}}.</p>"
            "<p><strong>Is your widget on every page?</strong> The AI can only talk to visitors "
            "on pages where the widget is installed. Check that the embed code is on every page.</p>"
            "<p><strong>Are you following up on leads?</strong> Go to your Leads page and check "
            "for any &ldquo;New&rdquo; leads you haven't contacted yet.</p>"
            "<p><strong>Set up automations:</strong> Go to Automations and create a follow-up "
            "sequence &mdash; emails that go out automatically after a lead comes in.</p>"
            "<p><a href='https://agentnexlify.vercel.app' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Open your dashboard &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 14,
        "min_hours": 335,
        "max_hours": 338,
        "subject": "You're leaving money on the table, {{owner_name}}",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>Two weeks in. Your AI assistant has been working 24/7 for {{business_name}}.</p>"
            "<p>Here's what you might be missing on the free plan:</p>"
            "<ul>"
            "<li><strong>Automated follow-ups</strong> &mdash; emails and SMS that fire instantly when a new lead comes in</li>"
            "<li><strong>SMS notifications</strong> &mdash; get a text the moment someone fills out your chat</li>"
            "<li><strong>Google Calendar sync</strong> &mdash; appointments appear on your calendar automatically</li>"
            "<li><strong>Review management</strong> &mdash; auto-request reviews, draft AI responses</li>"
            "<li><strong>Team collaboration</strong> &mdash; invite team members, assign leads, internal notes</li>"
            "</ul>"
            "<p>One captured lead that turns into a customer pays for months of AgentNexLiFy. "
            "The Growth plan is $199/month &mdash; less than a single Google ad click in most industries.</p>"
            "<p><a href='https://agentnexlify.vercel.app' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "See what you're missing &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
]


async def send_monthly_reports() -> int:
    """Send monthly performance reports to tenants with autopilot_enabled.

    Queries tenants where autopilot_enabled is true and last_monthly_report_at
    is NULL or more than 28 days ago. For each, builds a summary of the past
    month's conversations, leads, appointments, and reviews, then emails it to
    the owner. Updates last_monthly_report_at on the tenant after sending.

    Returns count of reports sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=28)).isoformat()
    month_start = (now - timedelta(days=30)).isoformat()
    sent = 0

    # Fetch tenants eligible for a monthly report:
    # autopilot_enabled = true AND (last_monthly_report_at IS NULL OR < 28 days ago)
    try:
        # First: tenants with autopilot_enabled and last_monthly_report_at IS NULL
        null_result = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .eq("autopilot_enabled", True)
            .is_("last_monthly_report_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
        # Second: tenants with autopilot_enabled and last_monthly_report_at < cutoff
        old_result = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .eq("autopilot_enabled", True)
            .lte("last_monthly_report_at", cutoff)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_monthly_reports: failed to query eligible tenants")
        return 0

    # Combine and deduplicate by tenant ID
    seen_ids: set[str] = set()
    eligible_tenants: list[dict] = []
    for tenant in (null_result.data or []) + (old_result.data or []):
        if tenant["id"] not in seen_ids:
            seen_ids.add(tenant["id"])
            eligible_tenants.append(tenant)

    for tenant in eligible_tenants:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        owner_name = tenant.get("owner_name") or "there"
        business_name = tenant.get("business_name") or "Your Business"

        # Gather metrics for the past 30 days
        conversations_count = 0
        leads_count = 0
        appointments_count = 0
        reviews_count = 0

        try:
            conv_result = (
                db.table("chat_messages")
                .select("session_id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .execute()
            )
            # Unique sessions = unique conversations
            if conv_result.data:
                unique_sessions = {m["session_id"] for m in conv_result.data}
                conversations_count = len(unique_sessions)
        except Exception:
            logger.warning("send_monthly_reports: failed to count conversations for tenant %s", tid, exc_info=True)

        try:
            # leads table uses client_id, not tenant_id
            leads_result = (
                db.table("leads")
                .select("id", count="exact")
                .eq("client_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            leads_count = leads_result.count or 0
        except Exception:
            logger.warning("send_monthly_reports: failed to count leads for tenant %s", tid, exc_info=True)

        try:
            appt_result = (
                db.table("appointments")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            appointments_count = appt_result.count or 0
        except Exception:
            logger.warning("send_monthly_reports: failed to count appointments for tenant %s", tid, exc_info=True)

        try:
            rev_result = (
                db.table("reviews")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            reviews_count = rev_result.count or 0
        except Exception:
            logger.warning("send_monthly_reports: failed to count reviews for tenant %s", tid, exc_info=True)

        # Build report email
        subject = f"Monthly Performance Report for {business_name}"
        body_html = (
            f"<h2>Hi {owner_name},</h2>"
            f"<p>Here's your monthly performance summary for <strong>{business_name}</strong>:</p>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;'>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Conversations</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{conversations_count}</td>"
            f"</tr>"
            f"<tr>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Leads Captured</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{leads_count}</td>"
            f"</tr>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Appointments Booked</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{appointments_count}</td>"
            f"</tr>"
            f"<tr>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Reviews Received</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{reviews_count}</td>"
            f"</tr>"
            f"</table>"
            f"<p>Keep up the great work! Visit your <a href='https://agentnexlify.vercel.app'>dashboard</a> "
            f"to see detailed analytics and manage your business.</p>"
            f"<p>Best,<br>The AgentNexLiFy Team</p>"
        )

        try:
            result = await send_email(
                to=email,
                subject=subject,
                body_html=body_html,
                tenant_id=tid,
            )
            if result.get("success"):
                sent += 1
                logger.info("Sent monthly report to %s (tenant %s): convos=%d leads=%d appts=%d reviews=%d",
                            email, tid, conversations_count, leads_count, appointments_count, reviews_count)

                # Update last_monthly_report_at on the tenant
                try:
                    db.table("tenants").update({
                        "last_monthly_report_at": now.isoformat(),
                    }).eq("id", tid).execute()
                except Exception:
                    logger.exception("send_monthly_reports: failed to update last_monthly_report_at for tenant %s", tid)
            else:
                logger.warning("send_monthly_reports: email send returned failure for tenant %s", tid)
        except Exception:
            logger.exception("send_monthly_reports: failed to send report email to %s (tenant %s)", email, tid)

    return sent


async def send_portal_links() -> int:
    """Send portal links to customers after job completion.

    When an appointment is marked 'completed' and the lead has a portal token,
    auto-send an email with the portal link. Tracks delivery via activity_log.
    """
    db = get_supabase()
    sent = 0

    try:
        # Find completed appointments without portal link sent
        appts = (
            db.table("appointments")
            .select("id, tenant_id, lead_id, customer_name, customer_email")
            .eq("status", "completed")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_portal_links: failed to query completed appointments")
        return 0

    for appt in appts.data or []:
        lead_id = appt.get("lead_id")
        customer_email = appt.get("customer_email")
        if not lead_id or not customer_email:
            continue

        tenant_id = appt["tenant_id"]
        activity_key = f"portal_link_sent_{appt['id']}"

        # Check if already sent
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", "portal_link_sent")
                .eq("description", activity_key)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            continue

        # Check if portal token exists
        try:
            tok_result = (
                db.table("portal_tokens")
                .select("token")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
        except Exception:
            continue

        if not tok_result.data:
            continue

        token = tok_result.data[0]["token"]
        portal_url = f"https://agentnexlify.vercel.app/client/{token}"

        # Get business name
        try:
            t_result = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
            biz_name = t_result.data[0]["business_name"] if t_result.data else "Our Team"
        except Exception:
            biz_name = "Our Team"

        customer_name = appt.get("customer_name") or "there"

        subject = f"Your service details from {biz_name}"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>Thank you for choosing <strong>{biz_name}</strong>!</p>"
            f"<p>You can view your service details, documents, and book again anytime:</p>"
            f"<p style='text-align:center;margin:20px 0;'>"
            f"<a href='{portal_url}' style='background:#3b82f6;color:#fff;padding:12px 24px;"
            f"border-radius:6px;text-decoration:none;font-weight:600;'>View Your Portal</a></p>"
            f"<p>Best,<br>The {biz_name} Team</p>"
        )

        try:
            result = await send_email(to=customer_email, subject=subject, body_html=body, tenant_id=tenant_id)
            if result.get("success"):
                sent += 1
                # Track delivery
                from backend.services.activity import log_activity
                log_activity(tenant_id=tenant_id, activity_type="portal_link_sent", description=activity_key)
                logger.info("Sent portal link to %s for appointment %s", customer_email, appt["id"])
        except Exception:
            logger.exception("Failed to send portal link for appointment %s", appt["id"])

    return sent


async def check_new_reviews() -> int:
    """Check for new reviews created in the last 60 seconds and notify tenant owners.

    For each new review, if the tenant has a notification_phone, sends an SMS alert
    and logs an activity_log entry with activity_type='new_review_alert'.

    Returns count of alerts sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(seconds=60)).isoformat()
    sent = 0

    try:
        recent_reviews = (
            db.table("reviews")
            .select("id, tenant_id, rating, author_name, platform, review_text")
            .gte("created_at", cutoff)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("check_new_reviews: failed to query recent reviews")
        return 0

    for review in recent_reviews.data or []:
        tenant_id = review.get("tenant_id")
        if not tenant_id:
            continue

        # Look up tenant notification phone
        try:
            tenant_result = (
                db.table("tenants")
                .select("notification_phone, business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception("check_new_reviews: failed to look up tenant %s", tenant_id)
            continue

        if not tenant_result.data:
            continue

        tenant = tenant_result.data[0]
        notification_phone = tenant.get("notification_phone")

        rating = review.get("rating", "?")
        author_name = review.get("author_name", "Someone")
        platform = review.get("platform", "unknown")
        review_text = review.get("review_text") or ""
        truncated_text = review_text[:80] + "..." if len(review_text) > 80 else review_text

        # Log activity regardless of whether SMS is sent
        from backend.services.activity import log_activity
        log_activity(
            tenant_id=tenant_id,
            activity_type="new_review_alert",
            description=(
                f"New {rating}-star review from {author_name} on {platform}"
            ),
            metadata={
                "review_id": review.get("id"),
                "rating": rating,
                "author_name": author_name,
                "platform": platform,
            },
        )

        # Send SMS if phone is configured
        if notification_phone:
            sms_body = (
                f"New {rating}-star review from {author_name} on {platform}: "
                f"'{truncated_text}'. Reply in your dashboard."
            )
            try:
                sms_ok = await send_sms(to=notification_phone, body=sms_body)
                if sms_ok:
                    sent += 1
                    logger.info(
                        "Sent new review alert SMS to %s for tenant %s (review %s)",
                        notification_phone, tenant_id, review.get("id"),
                    )
            except Exception:
                logger.exception(
                    "check_new_reviews: failed to send SMS to %s for tenant %s",
                    notification_phone, tenant_id,
                )

    return sent


async def send_onboarding_emails() -> int:
    """Send onboarding drip emails to tenants based on their signup date.

    Checks tenants created within specific time windows (Day 1, 3, 7, 14).
    Uses activity_log to track which emails have been sent (avoids duplicates).
    Returns count of emails sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    for step in _ONBOARDING_STEPS:
        window_start = now - timedelta(hours=step["max_hours"])
        window_end = now - timedelta(hours=step["min_hours"])
        activity_type = f"onboarding_email_day_{step['day']}"

        try:
            tenants = (
                db.table("tenants")
                .select("id, owner_name, owner_email, business_name")
                .gte("created_at", window_start.isoformat())
                .lte("created_at", window_end.isoformat())
                .limit(BATCH_LIMIT)
                .execute()
            )
        except Exception:
            logger.exception("send_onboarding_emails: failed to query tenants for day %d", step["day"])
            continue

        for tenant in tenants.data or []:
            tid = tenant["id"]
            email = tenant.get("owner_email")
            if not email:
                continue

            # Check if already sent
            try:
                existing = (
                    db.table("activity_log")
                    .select("id", count="exact")
                    .eq("tenant_id", tid)
                    .eq("activity_type", activity_type)
                    .limit(1)
                    .execute()
                )
                if existing.count and existing.count > 0:
                    continue
            except Exception:
                logger.warning("send_onboarding_emails: couldn't check activity_log for %s, skipping", tid)
                continue

            owner_name = tenant.get("owner_name") or "there"
            biz_name = tenant.get("business_name") or "your business"
            context = {"owner_name": owner_name, "business_name": biz_name}

            subject = render_template(step["subject"], context)
            body = render_template(step["body"], context)

            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    body_html=body,
                    tenant_id=tid,
                )
                if result.get("success"):
                    sent += 1
                    logger.info("Sent onboarding day %d email to %s (tenant %s)", step["day"], email, tid)
                    # Track in activity_log
                    db.table("activity_log").insert({
                        "tenant_id": tid,
                        "activity_type": activity_type,
                        "description": f"Onboarding email Day {step['day']} sent to {email}",
                    }).execute()
            except Exception:
                logger.exception("Failed to send onboarding day %d email to %s", step["day"], email)

    return sent
