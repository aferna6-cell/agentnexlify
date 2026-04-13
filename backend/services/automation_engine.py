"""Automation engine — triggers, processes, and executes email sequences."""

import asyncio

from backend.services.task_utils import safe_create_task
import html
import logging
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

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

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50

VALID_TRIGGER_EVENTS = {
    "new_lead",
    "lead_stage_change",
    "no_response_24h",
    "appointment_completed",
}


async def trigger_sequence(
    tenant_id: str,
    lead_id: str,
    trigger_event: str,
    trigger_context: dict[str, Any] | None = None,
) -> int:
    """Find matching active sequences and enroll the lead. Returns count of enrollments created."""
    db = get_service_supabase()
    trigger_context = trigger_context or {}

    # Find active sequences for this trigger event
    result = (
        tenant_table(db, "automation_sequences", tenant_id)
        .select("id, trigger_config")
        .eq("trigger_event", trigger_event)
        .eq("is_active", True)
        .execute()
    )

    sequences = result.data or []
    if not sequences:
        return 0

    # Filter sequences by trigger_context before fetching steps
    eligible_seqs = []
    for seq in sequences:
        if trigger_event == "lead_stage_change":
            target = (seq.get("trigger_config") or {}).get("target_stage")
            if target and target != trigger_context.get("new_stage"):
                continue
        eligible_seqs.append(seq)

    if not eligible_seqs:
        return 0

    # Batch-fetch the first active step for all eligible sequences in one query.
    # We fetch step_order + sequence_id so we can group in Python; limit to
    # len(eligible_seqs) rows because we only need one row per sequence and
    # Supabase returns them in step_order order.
    seq_ids = [s["id"] for s in eligible_seqs]
    steps_result = (
        db.table("automation_steps")
        .select("sequence_id, step_order, delay_minutes")
        .in_("sequence_id", seq_ids)
        .eq("is_active", True)
        .order("step_order")
        .limit(len(seq_ids) * 20)  # generous upper bound; deduped in Python below
        .execute()
    )
    # Build mapping sequence_id -> first step (lowest step_order)
    first_step_by_seq: dict[str, dict] = {}
    for step in steps_result.data or []:
        sid = step["sequence_id"]
        if sid not in first_step_by_seq:
            first_step_by_seq[sid] = step

    enrolled = 0
    for seq in eligible_seqs:
        first_step = first_step_by_seq.get(seq["id"])
        if not first_step:
            continue

        delay = first_step["delay_minutes"]
        next_run = datetime.now(timezone.utc) + timedelta(minutes=delay)

        try:
            tenant_table(db, "automation_executions", tenant_id).insert(
                {
                    "sequence_id": seq["id"],
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "current_step": 1,
                    "status": "in_progress",
                    "next_run_at": next_run.isoformat(),
                }
            ).execute()
            enrolled += 1
            logger.info(
                "Enrolled lead %s in sequence %s (trigger: %s)",
                lead_id,
                seq["id"],
                trigger_event,
            )
        except Exception as _enroll_exc:
            # UNIQUE constraint = already enrolled (expected). Other errors = real problems.
            err_str = str(_enroll_exc).lower()
            if "unique" in err_str or "duplicate" in err_str:
                logger.debug("Lead %s already enrolled in sequence %s", lead_id, seq["id"])
            else:
                logger.warning("Failed to enroll lead %s in sequence %s: %s", lead_id, seq["id"], _enroll_exc, exc_info=True)

    return enrolled


async def process_pending_steps() -> int:
    """Process all pending automation steps that are due. Returns count processed."""
    db = get_service_supabase()
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
    db = get_service_supabase()

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


async def check_no_response_leads() -> int:
    """Find leads with status 'new' that have had no chat activity in 24+ hours and trigger
    the no_response_24h automation sequence for each.

    Strategy (batched — <=5 DB round-trips for the read/check phase regardless of lead count):
      Q1. Load 'new' leads created more than 24h ago (batch, BATCH_LIMIT).
      Q2. Batch fetch automation_executions for all lead IDs where status is active or
          in_progress, then fetch those sequences' trigger_events. Build a set of lead IDs
          already enrolled in a no_response_24h sequence.
      Q3. Batch fetch conversations for all conversation IDs to get session_id mapping.
      Q4. Batch fetch latest chat_messages for all session IDs; deduplicate in Python to
          get the most recent timestamp per session_id.
      Then loop in Python to decide which leads to trigger.

    Returns count of sequences triggered.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    triggered = 0

    # Q1: fetch candidate leads
    try:
        leads_result = (
            db.table("leads")
            .select("id, client_id, conversation_id, created_at")
            .eq("status", "new")
            .lte("created_at", cutoff.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("check_no_response_leads: failed to query leads")
        return 0

    leads = leads_result.data or []
    if not leads:
        return 0

    all_lead_ids = [lead["id"] for lead in leads]
    all_conv_ids = [
        lead["conversation_id"] for lead in leads if lead.get("conversation_id")
    ]

    # Q2a: batch fetch active/in_progress executions for all leads
    already_enrolled_lead_ids: set[str] = set()
    try:
        exec_result = (
            db.table("automation_executions")
            .select("lead_id, sequence_id")
            .in_("lead_id", all_lead_ids)
            .in_("status", ["active", "in_progress"])
            .execute()
        )
        exec_rows = exec_result.data or []
    except Exception:
        logger.warning(
            "check_no_response_leads: batch enrollment check failed, proceeding without dedup",
            exc_info=True,
        )
        exec_rows = []

    if exec_rows:
        # Q2b: fetch trigger_events for the sequences referenced by those executions
        enrolled_seq_ids = list({row["sequence_id"] for row in exec_rows})
        try:
            seq_result = (
                db.table("automation_sequences")
                .select("id, trigger_event")
                .in_("id", enrolled_seq_ids)
                .execute()
            )
            no_response_seq_ids: set[str] = {
                s["id"]
                for s in (seq_result.data or [])
                if s.get("trigger_event") == "no_response_24h"
            }
        except Exception:
            logger.warning(
                "check_no_response_leads: batch sequence trigger_event check failed",
                exc_info=True,
            )
            no_response_seq_ids = set()

        for row in exec_rows:
            if row["sequence_id"] in no_response_seq_ids:
                already_enrolled_lead_ids.add(row["lead_id"])

    # Q3: batch fetch conversations to build conv_id -> session_id mapping
    conv_to_session: dict[str, str] = {}
    if all_conv_ids:
        try:
            conv_result = (
                db.table("conversations")
                .select("id, session_id")
                .in_("id", all_conv_ids)
                .execute()
            )
            for row in conv_result.data or []:
                if row.get("session_id"):
                    conv_to_session[row["id"]] = row["session_id"]
        except Exception:
            logger.warning(
                "check_no_response_leads: batch conversations lookup failed",
                exc_info=True,
            )

    # Q4: batch fetch latest chat_messages per session_id
    # Supabase returns rows in order; we take the first occurrence per session_id (latest).
    all_session_ids = list(set(conv_to_session.values()))
    session_last_message: dict[str, datetime] = {}
    if all_session_ids:
        try:
            msg_result = (
                db.table("chat_messages")
                .select("session_id, created_at")
                .in_("session_id", all_session_ids)
                .order("created_at", desc=True)
                .limit(len(all_session_ids) * 10)  # generous; deduplicated in Python
                .execute()
            )
            for row in msg_result.data or []:
                sid = row["session_id"]
                if sid not in session_last_message:
                    raw_ts = row["created_at"]
                    session_last_message[sid] = datetime.fromisoformat(
                        raw_ts.replace("Z", "+00:00")
                    )
        except Exception:
            logger.warning(
                "check_no_response_leads: batch chat_messages lookup failed",
                exc_info=True,
            )

    # Now evaluate each lead entirely in Python (no more DB calls in this loop)
    for lead in leads:
        lead_id = lead["id"]
        tenant_id = lead["client_id"]

        # Skip if already enrolled in a no_response_24h sequence
        if lead_id in already_enrolled_lead_ids:
            continue

        # Determine last message timestamp for this lead
        last_message_at = None
        conv_id = lead.get("conversation_id")
        if conv_id:
            session_id = conv_to_session.get(conv_id)
            if session_id:
                last_message_at = session_last_message.get(session_id)

        # Skip if there has been recent activity within 24h
        if last_message_at is not None and last_message_at > cutoff:
            continue  # Recent activity — skip

        try:
            count = await trigger_sequence(tenant_id, lead_id, "no_response_24h")
            if count:
                triggered += count
                logger.info(
                    "check_no_response_leads: triggered sequence for lead %s (tenant %s)",
                    lead_id,
                    tenant_id,
                )
        except Exception:
            logger.exception(
                "check_no_response_leads: trigger_sequence failed for lead %s", lead_id
            )

    return triggered


# ---------------------------------------------------------------------------
# Business-type-aware reminder extras
# ---------------------------------------------------------------------------

_REMINDER_EXTRAS: dict[str, list[str]] = {
    "dental": ["Insurance card", "Photo ID", "List of current medications"],
    "medical": [
        "Insurance card",
        "Photo ID",
        "List of current medications",
        "Medical records if transferring",
    ],
    "salon": ["Arrive 5-10 minutes early", "Photos of desired style (if applicable)"],
    "auto_shop": ["Vehicle registration", "Description of any issues"],
    "legal": ["Relevant documents or contracts", "Photo ID", "List of questions"],
    "realestate": ["Pre-approval letter (if buying)", "Photo ID"],
    "plumbing": [
        "Photos of the issue (if possible)",
        "Clear access to the problem area",
    ],
    "contractor": ["Photos of the project area", "Any permits or HOA approvals"],
    "fitness": ["Comfortable workout clothes", "Water bottle", "Towel"],
}


def _get_reminder_extras(business_type: str, notes: str) -> list[str]:
    """Return business-type-aware items to bring/prepare for an appointment."""
    extras = _REMINDER_EXTRAS.get(business_type, [])
    # Check if notes mention a specific service that needs extra instructions
    notes_lower = notes.lower()
    if business_type == "dental":
        if any(kw in notes_lower for kw in ["root canal", "surgery", "extraction"]):
            extras = extras + ["Arrange a ride home (sedation may be used)"]
        if "cleaning" in notes_lower or "checkup" in notes_lower:
            extras = extras + ["Floss before your visit"]
    return extras


async def send_appointment_reminders() -> int:
    """Check for upcoming appointments and send email/SMS reminders.

    Sends reminders at two windows:
    - 24 hours before (23h-25h window)
    - 1 hour before (30m-90m window)

    Uses a simple approach: query appointments in each window that haven't
    had a reminder sent yet (tracked via notes field with reminder tags).
    Returns count of reminders sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    reminder_windows = [
        {"label": "24h", "min_hours": 23, "max_hours": 25},
        {"label": "1h", "min_hours": 0.5, "max_hours": 1.5},
    ]

    for window in reminder_windows:
        window_start = now + timedelta(hours=window["min_hours"])
        window_end = now + timedelta(hours=window["max_hours"])

        # Use dedicated columns for dedup (falls back to notes field for pre-migration rows)
        reminder_col = f"reminder_{window['label']}_sent_at"

        try:
            appointments = (
                db.table("appointments")
                .select(
                    "id, tenant_id, customer_name, customer_email, customer_phone, "
                    "start_time, end_time, notes, status, reminder_24h_sent_at, reminder_1h_sent_at"
                )
                .gte("start_time", window_start.isoformat())
                .lte("start_time", window_end.isoformat())
                .eq("status", "booked")
                .execute()
            )
        except Exception:
            logger.exception(
                "send_appointment_reminders: failed to query appointments for %s window",
                window["label"],
            )
            continue

        for appt in appointments.data or []:
            # Skip if already sent — check column first, fall back to notes field
            if appt.get(reminder_col):
                continue
            reminder_tag = f"reminder_{window['label']}_sent"
            notes = appt.get("notes") or ""
            if reminder_tag in notes:
                continue

            tenant_id = appt["tenant_id"]

            try:
                tenant = (
                    db.table("tenants")
                    .select("business_name, owner_email, plan, business_type")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                if not tenant.data:
                    continue
                tenant_data = tenant.data[0]
                business_name = html.escape(
                    tenant_data.get("business_name") or "Our Team"
                )
            except Exception:
                logger.exception(
                    "send_appointment_reminders: failed to load tenant %s", tenant_id
                )
                continue

            # Format the appointment time nicely
            try:
                start_dt = datetime.fromisoformat(
                    appt["start_time"].replace("Z", "+00:00")
                )
                time_str = start_dt.strftime("%B %d at %I:%M %p")
            except Exception:
                time_str = appt["start_time"]

            customer_name = html.escape(appt.get("customer_name") or "there")
            customer_email = appt.get("customer_email")
            business_type = (tenant_data.get("business_type") or "").lower()

            # Business-type-aware reminder extras
            bring_items = _get_reminder_extras(business_type, appt.get("notes") or "")

            # Send email reminder
            if customer_email:
                subject_map = {
                    "24h": f"Reminder: Your appointment with {business_name} tomorrow",
                    "1h": f"Your appointment with {business_name} is in 1 hour",
                }
                bring_html = ""
                if bring_items and window["label"] == "24h":
                    bring_html = (
                        "<p><strong>Please remember to bring:</strong></p><ul>"
                        + "".join(f"<li>{item}</li>" for item in bring_items)
                        + "</ul>"
                    )

                body_map = {
                    "24h": (
                        f"<h2>Hi {customer_name},</h2>"
                        f"<p>This is a friendly reminder that you have an appointment "
                        f"with <strong>{business_name}</strong> scheduled for <strong>{time_str}</strong>.</p>"
                        f"{bring_html}"
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
                    await send_email(
                        to=customer_email,
                        subject=subject_map[window["label"]],
                        body_html=body_map[window["label"]],
                        tenant_id=tenant_id,
                    )
                    sent += 1
                    logger.info(
                        "Sent %s reminder for appointment %s to %s",
                        window["label"],
                        appt["id"],
                        customer_email,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send %s reminder for appointment %s",
                        window["label"],
                        appt["id"],
                    )

            # Send SMS reminder if phone available
            customer_phone = appt.get("customer_phone")
            if customer_phone:
                bring_sms = ""
                if bring_items and window["label"] == "24h":
                    bring_sms = " Please bring: " + ", ".join(bring_items[:3]) + "."

                sms_map = {
                    "24h": (
                        f"Hi {customer_name}, reminder: you have an appointment "
                        f"with {business_name} tomorrow ({time_str}).{bring_sms} "
                        f"Reply to reschedule."
                    ),
                    "1h": (
                        f"Hi {customer_name}, your appointment with "
                        f"{business_name} is in 1 hour ({time_str}). See you soon!"
                    ),
                }
                try:
                    if check_sms_rate_limit(
                        tenant_id, tenant_data.get("plan") or "free"
                    ):
                        await send_sms(to=customer_phone, body=sms_map[window["label"]])
                        increment_sms_count(tenant_id)
                        sent += 1
                except Exception:
                    logger.exception(
                        "Failed to send SMS %s reminder for appointment %s",
                        window["label"],
                        appt["id"],
                    )

            # Mark reminder as sent using dedicated column (+ notes fallback for compat)
            update_payload = {
                reminder_col: datetime.now(timezone.utc).isoformat(),
            }
            try:
                db.table("appointments").update(update_payload).eq(
                    "id", appt["id"]
                ).execute()
            except Exception:
                # Column may not exist yet (pre-migration) — fall back to notes
                updated_notes = (
                    f"{notes}\n{reminder_tag}".strip() if notes else reminder_tag
                )
                try:
                    db.table("appointments").update({"notes": updated_notes}).eq(
                        "id", appt["id"]
                    ).execute()
                except Exception:
                    logger.exception(
                        "Failed to mark reminder sent for appointment %s", appt["id"]
                    )

    return sent


# ---------------------------------------------------------------------------
# Rebook automation — suggest next appointment after completion
# ---------------------------------------------------------------------------

_REBOOK_INTERVALS: dict[str, tuple[int, str]] = {
    "dental": (180, "6-month checkup and cleaning"),
    "medical": (365, "annual physical"),
    "salon": (42, "next appointment"),
    "fitness": (30, "next session"),
}


async def send_rebook_suggestions() -> int:
    """After appointment completion, suggest rebooking for relevant business types.

    Checks completed appointments from 24-48 hours ago. Sends one rebook
    suggestion per appointment. Deduped via activity_log.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    # Look at appointments completed 24-48h ago
    window_start = now - timedelta(hours=48)
    window_end = now - timedelta(hours=24)

    try:
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, lead_id, updated_at"
            )
            .eq("status", "completed")
            .gte("updated_at", window_start.isoformat())
            .lte("updated_at", window_end.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception(
            "send_rebook_suggestions: failed to query completed appointments"
        )
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, business_type, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        btype = (tenant.get("business_type") or "").lower()
        if btype not in _REBOOK_INTERVALS:
            continue

        days, suggestion = _REBOOK_INTERVALS[btype]

        # Dedup: check if we already sent a rebook for this appointment
        try:
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", appt.get("lead_id"))
                .eq("activity_type", "rebook_suggestion_sent")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in automation trigger", exc_info=True)

        business_name = html.escape(tenant.get("business_name") or "Us")
        customer_name = html.escape(appt.get("customer_name") or "there")
        customer_email = appt.get("customer_email")

        if customer_email:
            subject = f"Time to schedule your {suggestion} with {business_name}"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>We hope your recent visit to <strong>{business_name}</strong> went well!</p>"
                f"<p>We recommend scheduling your next <strong>{suggestion}</strong> in about "
                f"<strong>{days} days</strong> to stay on track.</p>"
                f"<p>Reply to this email or contact us to book your next appointment.</p>"
                f"<p>Best,<br>The {business_name} Team</p>"
            )
            try:
                result = await send_email(
                    to=customer_email,
                    subject=subject,
                    body_html=body,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    sent += 1
            except Exception:
                logger.exception(
                    "Failed to send rebook suggestion for appointment %s", appt["id"]
                )

        # Log to prevent duplicates
        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "lead_id": appt.get("lead_id"),
                    "activity_type": "rebook_suggestion_sent",
                    "description": f"Rebook suggestion sent: {suggestion} in {days} days",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log rebook suggestion for appointment %s",
                appt["id"],
                exc_info=True,
            )

    return sent


# ---------------------------------------------------------------------------
# Post-appointment aftercare instructions
# ---------------------------------------------------------------------------

_AFTERCARE_TEMPLATES: dict[str, dict[str, str]] = {
    "dental": {
        "default": "Thank you for your visit! Please wait 30 minutes before eating or drinking. If you experience any sensitivity, over-the-counter pain relief should help.",
        "cleaning": "Your teeth have been professionally cleaned! Avoid dark foods and beverages for 24 hours. Continue brushing twice daily and flossing.",
        "filling": "Your filling is complete. The numbness should wear off in 2-3 hours. Avoid chewing on the treated side until then. If you experience persistent pain, please contact us.",
        "extraction": "Please bite on the gauze for 30-45 minutes. Avoid spitting, straws, and hot liquids for 24 hours. Rinse gently with warm salt water after 24 hours.",
        "root canal": "Some tenderness is normal for a few days. Avoid chewing on the treated tooth until your permanent crown is placed. Take prescribed medications as directed.",
    },
    "medical": {
        "default": "Thank you for your visit. Follow the care plan discussed during your appointment. Contact us if symptoms worsen.",
    },
    "salon": {
        "default": "Thank you for visiting us! To maintain your new look, follow the care tips your stylist shared.",
        "color": "Avoid washing your hair for 48 hours to let the color set. Use color-safe shampoo and conditioner.",
    },
    "fitness": {
        "default": "Great session! Stay hydrated, stretch, and rest as needed. See you next time!",
    },
    "auto_shop": {
        "default": "Your vehicle service is complete. Please keep your receipt for warranty purposes. If you notice any issues, bring it back and we'll take a look.",
    },
}


async def send_aftercare_instructions() -> int:
    """Send aftercare instructions 2-4 hours after appointment completion.

    Deduped via activity_log (aftercare_sent per appointment).
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    # Check appointments completed 2-4 hours ago
    window_start = now - timedelta(hours=4)
    window_end = now - timedelta(hours=2)

    try:
        appts = (
            db.table("appointments")
            .select("id, tenant_id, customer_name, customer_email, notes, updated_at")
            .eq("status", "completed")
            .gte("updated_at", window_start.isoformat())
            .lte("updated_at", window_end.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_aftercare_instructions: failed to query")
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]
        appt_id = appt["id"]

        # Dedup
        try:
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", f"aftercare_sent_{appt_id}")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in automation trigger", exc_info=True)

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, business_type, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant or (tenant.get("plan") or "free") == "free":
            continue

        btype = (tenant.get("business_type") or "").lower()
        templates = _AFTERCARE_TEMPLATES.get(btype)
        if not templates:
            continue

        if not appt.get("customer_email"):
            continue

        # Pick the right template based on notes/service type
        notes_lower = (appt.get("notes") or "").lower()
        message = templates.get("default", "")
        for keyword, template in templates.items():
            if keyword != "default" and keyword in notes_lower:
                message = template
                break

        if not message:
            continue

        business_name = html.escape(tenant.get("business_name") or "Us")
        customer_name = html.escape(appt.get("customer_name") or "there")

        subject = f"Post-visit care instructions from {business_name}"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>{html.escape(message)}</p>"
            f"<p>If you have any questions or concerns, don't hesitate to reach out.</p>"
            f"<p>Best,<br>The {business_name} Team</p>"
        )

        try:
            result = await send_email(
                to=appt["customer_email"],
                subject=subject,
                body_html=body,
                tenant_id=tenant_id,
            )
            if result.get("success"):
                sent += 1
        except Exception:
            logger.exception("Failed to send aftercare for appointment %s", appt_id)

        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "activity_type": f"aftercare_sent_{appt_id}",
                    "description": f"Aftercare instructions sent to {customer_name}",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log aftercare for appointment %s", appt_id, exc_info=True
            )

    return sent


async def send_pending_review_requests() -> int:
    """Check for completed appointments that need review requests sent.

    Queries appointments with status='completed' where review_request_sent_at
    is null and the tenant has review requests enabled. Respects the configured
    delay (hours since completion). Sends via email, SMS, or both.

    Returns count of review requests sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    try:
        # Get completed appointments that haven't had review requests sent
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, updated_at, lead_id"
            )
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
                    .select(
                        "business_name, google_review_link, google_place_id, review_request_config, plan"
                    )
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.exception(
                    "send_pending_review_requests: failed to load tenant %s", tenant_id
                )
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        config = tenant.get("review_request_config") or {}
        if not config.get("enabled"):
            continue

        # Build review link: prefer direct Google write-review URL if place_id exists,
        # otherwise fall back to the manually configured google_review_link.
        place_id = tenant.get("google_place_id")
        if place_id:
            review_link = (
                f"https://search.google.com/local/writereview?placeid={place_id}"
            )
        else:
            review_link = tenant.get("google_review_link") or ""

        if not review_link:
            continue

        # Check delay — default changed from 0 to 2 hours so review requests
        # are sent after a short cool-down rather than immediately on completion.
        delay_hours = config.get("delay_hours", 2)
        try:
            completed_at = datetime.fromisoformat(
                appt["updated_at"].replace("Z", "+00:00")
            )
        except Exception:
            logger.warning("Failed to parse appointment timestamp", exc_info=True)
            continue

        if (now - completed_at).total_seconds() < delay_hours * 3600:
            continue

        business_name = html.escape(tenant.get("business_name") or "Our Team")
        customer_name = html.escape(appt.get("customer_name") or "there")
        method = config.get("method", "email")

        # CAN-SPAM: skip if lead has unsubscribed
        lead_id = appt.get("lead_id")
        if lead_id:
            try:
                lr = (
                    db.table("leads")
                    .select("unsubscribed")
                    .eq("id", lead_id)
                    .limit(1)
                    .execute()
                )
                if lr.data and lr.data[0].get("unsubscribed"):
                    continue
            except Exception:
                logger.debug("Failed to check unsubscribe status for lead %s, proceeding (fail-open)", lead_id, exc_info=True)

        # Send email review request
        if method in ("email", "both") and appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            safe_review_link = html.escape(review_link, quote=True)
            subject = f"How was your experience with {business_name}?"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>Thank you for your recent visit with <strong>{business_name}</strong>! "
                f"We hope everything went well.</p>"
                f"<p>We'd really appreciate it if you could take a moment to share your experience:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{safe_review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
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
                    logger.info(
                        "Sent review request email for appointment %s", appt["id"]
                    )
            except Exception:
                logger.exception(
                    "Failed to send review request email for appointment %s", appt["id"]
                )

        # Send SMS review request
        if method in ("sms", "both") and appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, thanks for visiting {business_name}! "
                f"We'd love your feedback. Leave a review here: {review_link}"
            )
            try:
                plan = tenant.get("plan") or "free"
                if check_sms_rate_limit(tenant_id, plan):
                    sms_ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if sms_ok:
                        increment_sms_count(tenant_id)
                        sent += 1
                        logger.info(
                            "Sent review request SMS for appointment %s", appt["id"]
                        )
            except Exception:
                logger.exception(
                    "Failed to send review request SMS for appointment %s", appt["id"]
                )

        # Mark as sent regardless of success to avoid retry loops
        try:
            db.table("appointments").update(
                {
                    "review_request_sent_at": now.isoformat(),
                }
            ).eq("id", appt["id"]).execute()
        except Exception:
            logger.exception(
                "Failed to mark review request sent for appointment %s", appt["id"]
            )

    # --- Follow-up reminder loop ---
    # Find appointments where a review request was sent 48+ hours ago but no
    # follow-up has been sent yet. Dedup via activity_log entries.
    sent += await _send_review_followups(db, now, tenant_cache)

    return sent


async def _send_review_followups(
    db: Any,
    now: datetime,
    tenant_cache: dict[str, dict],
) -> int:
    """Send one follow-up review reminder for requests sent 48+ hours ago with no prior followup.

    Deduplication: checks activity_log for activity_type='review_followup_{appointment_id}'.
    Returns count of follow-ups sent.
    """
    sent = 0
    followup_cutoff = now - timedelta(hours=48)

    try:
        followup_appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, lead_id, review_request_sent_at"
            )
            .eq("status", "completed")
            .not_.is_("review_request_sent_at", "null")
            .lte("review_request_sent_at", followup_cutoff.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("_send_review_followups: failed to query appointments")
        return 0

    for appt in followup_appts.data or []:
        appt_id = appt["id"]
        tenant_id = appt["tenant_id"]
        followup_activity_type = f"review_followup_{appt_id}"

        # Dedup check: skip if a follow-up was already sent for this appointment
        try:
            dedup_result = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", followup_activity_type)
                .limit(1)
                .execute()
            )
            if dedup_result.data:
                continue  # Already sent a follow-up for this appointment
        except Exception:
            logger.warning(
                "_send_review_followups: dedup check failed for appointment %s",
                appt_id,
                exc_info=True,
            )
            continue  # Skip on dedup failure to avoid duplicate sends

        # Load tenant if not already cached
        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select(
                        "business_name, google_review_link, google_place_id, review_request_config, plan"
                    )
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.exception(
                    "_send_review_followups: failed to load tenant %s", tenant_id
                )
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        config = tenant.get("review_request_config") or {}
        if not config.get("enabled"):
            continue

        # Build review link (same logic as main loop)
        place_id = tenant.get("google_place_id")
        if place_id:
            review_link = (
                f"https://search.google.com/local/writereview?placeid={place_id}"
            )
        else:
            review_link = tenant.get("google_review_link") or ""

        if not review_link:
            continue

        business_name = html.escape(tenant.get("business_name") or "Our Team")
        customer_name = html.escape(appt.get("customer_name") or "there")
        method = config.get("method", "email")

        # CAN-SPAM: skip if lead has unsubscribed
        lead_id = appt.get("lead_id")
        if lead_id:
            try:
                lr = (
                    db.table("leads")
                    .select("unsubscribed")
                    .eq("id", lead_id)
                    .limit(1)
                    .execute()
                )
                if lr.data and lr.data[0].get("unsubscribed"):
                    continue
            except Exception:
                logger.debug("Failed to check unsubscribe status for lead %s, proceeding (fail-open)", lead_id, exc_info=True)

        followup_sent = False

        # Send follow-up email
        if method in ("email", "both") and appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            safe_review_link = html.escape(review_link, quote=True)
            subject = f"Still happy to help — leave us a review, {customer_name}!"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>We wanted to follow up on our earlier message. We'd love to hear "
                f"about your experience with <strong>{business_name}</strong>.</p>"
                f"<p>If you have a moment, we'd really appreciate a quick review:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{safe_review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;font-weight:600;">Leave a Review</a></p>'
                f"<p>It only takes a minute and means a lot to us. Thank you!</p>"
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
                    followup_sent = True
                    logger.info(
                        "Sent review follow-up email for appointment %s", appt_id
                    )
            except Exception:
                logger.exception(
                    "Failed to send review follow-up email for appointment %s", appt_id
                )

        # Send follow-up SMS
        if method in ("sms", "both") and appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, just a friendly reminder from {business_name} — "
                f"we'd love your review! {review_link}"
            )
            try:
                plan = tenant.get("plan") or "free"
                if check_sms_rate_limit(tenant_id, plan):
                    sms_ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if sms_ok:
                        increment_sms_count(tenant_id)
                        sent += 1
                        followup_sent = True
                        logger.info(
                            "Sent review follow-up SMS for appointment %s", appt_id
                        )
            except Exception:
                logger.exception(
                    "Failed to send review follow-up SMS for appointment %s", appt_id
                )

        # Record the follow-up in activity_log for dedup on future loop iterations
        if followup_sent:
            try:
                activity_row: dict[str, Any] = {
                    "tenant_id": tenant_id,
                    "activity_type": followup_activity_type,
                    "description": f"Review follow-up sent for appointment {appt_id}",
                    "metadata": {"appointment_id": appt_id},
                }
                if lead_id:
                    activity_row["lead_id"] = lead_id
                db.table("activity_log").insert(activity_row).execute()
            except Exception:
                logger.warning(
                    "_send_review_followups: failed to log followup activity for appointment %s",
                    appt_id,
                    exc_info=True,
                )

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
            "<p>Go to your <a href='https://app.agentnexlify.com'>FAQ Manager</a> and add the "
            "questions your customers ask the most: your hours, pricing, service area, what makes "
            "you different, and how to book.</p>"
            "<p>Each FAQ you add makes the AI smarter. Customers get instant, accurate answers "
            "instead of &ldquo;I'm not sure.&rdquo;</p>"
            "<p><strong>Bonus:</strong> If you have a website, go to Settings and paste your URL. "
            "Click &ldquo;Scan Website&rdquo; &mdash; the AI will read your site and learn your "
            "services automatically.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
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
            "<a href='https://app.agentnexlify.com'>Conversations</a> to see what visitors "
            "asked and how the AI responded.</p>"
            "<p><strong>Improve the AI with one click:</strong> See a response you don't love? "
            "Click the thumbs-down button and type what the AI <em>should</em> have said. "
            "It learns from your corrections.</p>"
            "<p><strong>Check your leads:</strong> Go to Leads to see everyone who shared their "
            "contact info. Follow up within an hour for the best results.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
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
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
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
            "The Growth plan is $249/month &mdash; less than a single Google ad click in most industries. "
            "Now with SEO audit tools and AI content writer included.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
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
    db = get_service_supabase()
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
            logger.warning(
                "send_monthly_reports: failed to count conversations for tenant %s",
                tid,
                exc_info=True,
            )

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
            logger.warning(
                "send_monthly_reports: failed to count leads for tenant %s",
                tid,
                exc_info=True,
            )

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
            logger.warning(
                "send_monthly_reports: failed to count appointments for tenant %s",
                tid,
                exc_info=True,
            )

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
            logger.warning(
                "send_monthly_reports: failed to count reviews for tenant %s",
                tid,
                exc_info=True,
            )

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
            f"<p>Keep up the great work! Visit your <a href='https://app.agentnexlify.com'>dashboard</a> "
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
                logger.info(
                    "Sent monthly report to %s (tenant %s): convos=%d leads=%d appts=%d reviews=%d",
                    email,
                    tid,
                    conversations_count,
                    leads_count,
                    appointments_count,
                    reviews_count,
                )

                # Update last_monthly_report_at on the tenant
                try:
                    db.table("tenants").update(
                        {
                            "last_monthly_report_at": now.isoformat(),
                        }
                    ).eq("id", tid).execute()
                except Exception:
                    logger.exception(
                        "send_monthly_reports: failed to update last_monthly_report_at for tenant %s",
                        tid,
                    )
            else:
                logger.warning(
                    "send_monthly_reports: email send returned failure for tenant %s",
                    tid,
                )
        except Exception:
            logger.exception(
                "send_monthly_reports: failed to send report email to %s (tenant %s)",
                email,
                tid,
            )

    return sent


async def send_portal_links() -> int:
    """Send portal links to customers after job completion.

    When an appointment is marked 'completed' and the lead has a portal token,
    auto-send an email with the portal link. Tracks delivery via activity_log.
    """
    db = get_service_supabase()
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
            logger.warning("Dedup check failed in review request trigger", exc_info=True)
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
            logger.warning("Failed to insert review request record", exc_info=True)
            continue

        if not tok_result.data:
            continue

        token = tok_result.data[0]["token"]
        portal_url = f"https://app.agentnexlify.com/client/{token}"

        # Get business name
        try:
            t_result = (
                db.table("tenants")
                .select("business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            biz_name = (
                t_result.data[0]["business_name"] if t_result.data else "Our Team"
            )
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
            result = await send_email(
                to=customer_email, subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
                # Track delivery
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tenant_id,
                    activity_type="portal_link_sent",
                    description=activity_key,
                )
                logger.info(
                    "Sent portal link to %s for appointment %s",
                    customer_email,
                    appt["id"],
                )
        except Exception:
            logger.exception(
                "Failed to send portal link for appointment %s", appt["id"]
            )

    return sent


async def send_csat_surveys() -> int:
    """Send CSAT surveys for recently completed conversations.

    Checks for conversations that ended 1-2 hours ago (to give a cooling period)
    where the lead has an email and no survey has been sent yet.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=2)).isoformat()
    window_end = (now - timedelta(hours=1)).isoformat()
    sent = 0

    try:
        # Find completed appointments in the window
        appts = (
            db.table("appointments")
            .select("id, tenant_id, lead_id, customer_email, customer_name")
            .eq("status", "completed")
            .gte("updated_at", window_start)
            .lte("updated_at", window_end)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_csat_surveys: failed to query appointments")
        return 0

    for appt in appts.data or []:
        email = appt.get("customer_email")
        if not email:
            continue

        tenant_id = appt["tenant_id"]
        activity_key = f"csat_sent_{appt['id']}"

        # Check if already sent
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", "csat_sent")
                .eq("description", activity_key)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning("Dedup check failed in follow-up review trigger", exc_info=True)
            continue

        # Get business name
        try:
            t = (
                db.table("tenants")
                .select("business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            biz_name = t.data[0]["business_name"] if t.data else "us"
        except Exception:
            biz_name = "us"

        customer_name = appt.get("customer_name") or "there"
        survey_token = f"{tenant_id}:appt_{appt['id']}"
        survey_url = f"https://app.agentnexlify.com/survey?token={survey_token}"

        subject = f"How was your experience with {biz_name}?"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>Thank you for choosing <strong>{biz_name}</strong>!</p>"
            f"<p>We'd love to hear about your experience. It takes just 10 seconds:</p>"
            f"<p style='text-align:center;margin:20px 0;font-size:28px;'>"
            f"<a href='{survey_url}&r=1' style='text-decoration:none;margin:0 4px;'>1</a> "
            f"<a href='{survey_url}&r=2' style='text-decoration:none;margin:0 4px;'>2</a> "
            f"<a href='{survey_url}&r=3' style='text-decoration:none;margin:0 4px;'>3</a> "
            f"<a href='{survey_url}&r=4' style='text-decoration:none;margin:0 4px;'>4</a> "
            f"<a href='{survey_url}&r=5' style='text-decoration:none;margin:0 4px;'>5</a>"
            f"</p>"
            f"<p style='text-align:center;color:#888;font-size:12px;'>1 = Poor &nbsp;&nbsp; 5 = Excellent</p>"
            f"<p>Best,<br>The {biz_name} Team</p>"
        )

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tenant_id,
                    activity_type="csat_sent",
                    description=activity_key,
                )
                logger.info(
                    "Sent CSAT survey to %s for appointment %s", email, appt["id"]
                )
        except Exception:
            logger.exception(
                "Failed to send CSAT survey for appointment %s", appt["id"]
            )

    return sent


async def check_new_reviews() -> int:
    """Check for new reviews created in the last 60 seconds and notify tenant owners.

    For each new review, if the tenant has a notification_phone, sends an SMS alert
    and logs an activity_log entry with activity_type='new_review_alert'.

    Returns count of alerts sent.
    """
    db = get_service_supabase()
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
            logger.exception(
                "check_new_reviews: failed to look up tenant %s", tenant_id
            )
            continue

        if not tenant_result.data:
            continue

        tenant = tenant_result.data[0]
        notification_phone = tenant.get("notification_phone")

        rating = review.get("rating", "?")
        author_name = review.get("author_name", "Someone")
        platform = review.get("platform", "unknown")
        review_text = review.get("review_text") or ""
        truncated_text = (
            review_text[:80] + "..." if len(review_text) > 80 else review_text
        )

        # Log activity regardless of whether SMS is sent
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=tenant_id,
            activity_type="new_review_alert",
            description=(f"New {rating}-star review from {author_name} on {platform}"),
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
                        notification_phone,
                        tenant_id,
                        review.get("id"),
                    )
            except Exception:
                logger.exception(
                    "check_new_reviews: failed to send SMS to %s for tenant %s",
                    notification_phone,
                    tenant_id,
                )

    return sent


async def send_onboarding_emails() -> int:
    """Send onboarding drip emails to tenants based on their signup date.

    Checks tenants created within specific time windows (Day 1, 3, 7, 14).
    Uses activity_log to track which emails have been sent (avoids duplicates).
    Returns count of emails sent.
    """
    db = get_service_supabase()
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
            logger.exception(
                "send_onboarding_emails: failed to query tenants for day %d",
                step["day"],
            )
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
                logger.warning(
                    "send_onboarding_emails: couldn't check activity_log for %s, skipping",
                    tid,
                )
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
                    logger.info(
                        "Sent onboarding day %d email to %s (tenant %s)",
                        step["day"],
                        email,
                        tid,
                    )
                    # Track in activity_log
                    db.table("activity_log").insert(
                        {
                            "tenant_id": tid,
                            "activity_type": activity_type,
                            "description": f"Onboarding email Day {step['day']} sent to {email}",
                        }
                    ).execute()
            except Exception:
                logger.exception(
                    "Failed to send onboarding day %d email to %s", step["day"], email
                )

    return sent


async def send_invoice_payment_reminders() -> int:
    """Send reminders for overdue or soon-due unpaid invoices.

    Logic:
    - Invoices with status='sent' and due_date <= today -> mark as 'overdue' and send reminder
    - Invoices with status='sent' and due_date = tomorrow -> send a friendly "due tomorrow" nudge
    - Uses activity_log to dedup (one reminder per invoice per day)

    Returns count of reminders sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    activity_date_tag = f"invoice_reminder_{today}"
    sent = 0

    # Fetch sent invoices that are due today or earlier (overdue) or due tomorrow
    try:
        invoices = (
            db.table("invoices")
            .select(
                "id, tenant_id, lead_id, invoice_number, total, due_date, status, stripe_payment_link"
            )
            .eq("status", "sent")
            .lte("due_date", tomorrow)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_invoice_payment_reminders: failed to query invoices")
        return 0

    for inv in invoices.data or []:
        inv_id = inv["id"]
        tenant_id = inv.get("tenant_id")
        lead_id = inv.get("lead_id")
        due_date = inv.get("due_date", "")

        if not tenant_id or not lead_id:
            continue

        # Check dedup — one reminder per invoice per day
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", activity_date_tag)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning(
                "send_invoice_payment_reminders: dedup check failed for invoice %s",
                inv_id,
            )
            continue

        # Mark overdue if due_date <= today
        is_overdue = due_date <= today
        if is_overdue:
            try:
                db.table("invoices").update({"status": "overdue"}).eq(
                    "id", inv_id
                ).execute()
            except Exception:
                logger.warning("Failed to mark invoice %s as overdue", inv_id)

        # Get lead contact info
        try:
            lead_result = (
                db.table("leads")
                .select("name, email, phone")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "send_invoice_payment_reminders: failed to look up lead %s", lead_id
            )
            continue

        if not lead_result.data:
            continue
        lead = lead_result.data[0]

        # Get business info
        try:
            tenant_result = (
                db.table("tenants")
                .select("business_name, owner_email")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "send_invoice_payment_reminders: failed to look up tenant %s", tenant_id
            )
            continue

        if not tenant_result.data:
            continue
        tenant_info = tenant_result.data[0]

        biz_name = tenant_info.get("business_name") or "Your Service Provider"
        cust_name = lead.get("name") or "Customer"
        inv_num = inv.get("invoice_number") or "N/A"
        total = inv.get("total", 0)
        pay_link = inv.get("stripe_payment_link") or ""

        if is_overdue:
            subject = f"Payment overdue — Invoice {inv_num} from {biz_name}"
            body_text = (
                f"Hi {cust_name}, this is a reminder that Invoice {inv_num} "
                f"for ${total:.2f} was due on {due_date} and is now overdue."
            )
        else:
            subject = f"Payment reminder — Invoice {inv_num} due tomorrow"
            body_text = (
                f"Hi {cust_name}, just a friendly reminder that Invoice {inv_num} "
                f"for ${total:.2f} from {biz_name} is due tomorrow ({due_date})."
            )

        pay_section = f" Pay now: {pay_link}" if pay_link else ""

        # Send email
        email = lead.get("email")
        if email:
            html_body = (
                f"<div style='font-family:sans-serif;max-width:600px;'>"
                f"<h2 style='color:#1e293b;'>{subject}</h2>"
                f"<p style='color:#374151;font-size:16px;'>{body_text}</p>"
            )
            if pay_link:
                html_body += (
                    f"<p style='margin-top:24px;'>"
                    f"<a href='{pay_link}' style='background:#3b82f6;color:white;padding:12px 24px;"
                    f"border-radius:8px;text-decoration:none;font-weight:bold;'>Pay Now</a></p>"
                )
            html_body += (
                f"<p style='color:#6b7280;margin-top:24px;'>— {biz_name}</p></div>"
            )

            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    body_html=html_body,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    sent += 1
                    logger.info(
                        "Sent invoice reminder email for %s to %s", inv_num, email
                    )
            except Exception:
                logger.exception(
                    "Failed to send invoice reminder email for %s", inv_num
                )

        # Send SMS
        phone = lead.get("phone")
        if phone:
            sms_body = f"{body_text}{pay_section}"
            try:
                sms_ok = await send_sms(to=phone, body=sms_body)
                if sms_ok:
                    sent += 1
                    logger.info(
                        "Sent invoice reminder SMS for %s to %s", inv_num, phone
                    )
            except Exception:
                logger.exception("Failed to send invoice reminder SMS for %s", inv_num)

        # Track in activity_log for dedup
        try:
            from backend.services.activity import log_activity

            log_activity(
                tenant_id=tenant_id,
                lead_id=lead_id,
                activity_type=activity_date_tag,
                description=f"{'Overdue' if is_overdue else 'Due tomorrow'} reminder sent for Invoice {inv_num} (${total:.2f})",
                metadata={"invoice_id": inv_id, "is_overdue": is_overdue},
            )
        except Exception:
            logger.warning("Failed to log activity for invoice reminder %s", inv_id)

    return sent


async def send_weekly_intelligence_briefs() -> int:
    """Send weekly AI-powered business intelligence briefs to paid tenants.

    Runs in the automation loop. Checks day-of-week (Monday only) and whether
    a brief was already sent this week (via activity_log dedup).

    Gathers 7-day metrics (leads, conversations, appointments, invoices, pipeline),
    sends them to Claude for analysis, and emails the AI-generated insights.

    Returns count of briefs sent.
    """
    from backend.services.llm_runtime import call_claude_messages_sync

    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    # Only run on Mondays (weekday() == 0)
    if now.weekday() != 0:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_brief_{now.date().isoformat()}"
    sent = 0

    # Fetch paid tenants (not free plan)
    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name, plan, business_type")
            .neq("plan", "free")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_weekly_intelligence_briefs: failed to query tenants")
        return 0

    for tenant in tenants.data or []:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        # Dedup — one brief per tenant per week
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("activity_type", week_tag)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning(
                "send_weekly_intelligence_briefs: dedup check failed for tenant %s", tid
            )
            continue

        # Gather 7-day metrics
        metrics = {}

        # Leads (uses client_id, not tenant_id)
        try:
            leads_result = (
                db.table("leads")
                .select("id, status, lead_temperature, deal_value", count="exact")
                .eq("client_id", tid)
                .gte("created_at", week_start)
                .limit(200)
                .execute()
            )
            leads_data = leads_result.data or []
            metrics["new_leads"] = len(leads_data)
            metrics["hot_leads"] = sum(
                1 for l in leads_data if l.get("lead_temperature") == "hot"
            )
            metrics["total_deal_value"] = sum(
                float(l.get("deal_value") or 0) for l in leads_data
            )
        except Exception:
            metrics["new_leads"] = 0
            logger.warning(
                "weekly brief: failed to count leads for %s", tid, exc_info=True
            )

        # Conversations
        try:
            conv_result = (
                db.table("conversations")
                .select("id, status", count="exact")
                .eq("client_id", tid)
                .gte("created_at", week_start)
                .limit(1)
                .execute()
            )
            metrics["conversations"] = conv_result.count or 0
        except Exception:
            metrics["conversations"] = 0

        # Appointments
        try:
            appt_result = (
                db.table("appointments")
                .select("id, status", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(1)
                .execute()
            )
            metrics["appointments"] = appt_result.count or 0
        except Exception:
            metrics["appointments"] = 0

        # Invoices
        try:
            inv_result = (
                db.table("invoices")
                .select("id, status, total", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(200)
                .execute()
            )
            inv_data = inv_result.data or []
            metrics["invoices_sent"] = sum(
                1 for i in inv_data if i.get("status") in ("sent", "viewed", "paid")
            )
            metrics["invoices_paid"] = sum(
                1 for i in inv_data if i.get("status") == "paid"
            )
            metrics["revenue_collected"] = sum(
                float(i.get("total") or 0)
                for i in inv_data
                if i.get("status") == "paid"
            )
        except Exception:
            metrics["invoices_sent"] = 0
            metrics["invoices_paid"] = 0
            metrics["revenue_collected"] = 0

        # Reviews
        try:
            rev_result = (
                db.table("reviews")
                .select("id, rating", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(50)
                .execute()
            )
            rev_data = rev_result.data or []
            metrics["new_reviews"] = len(rev_data)
            metrics["avg_rating"] = round(
                sum(r.get("rating", 0) for r in rev_data) / max(len(rev_data), 1), 1
            )
        except Exception:
            metrics["new_reviews"] = 0
            metrics["avg_rating"] = 0

        # Action items pending
        try:
            actions_result = (
                db.table("action_items")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            metrics["pending_actions"] = actions_result.count or 0
        except Exception:
            metrics["pending_actions"] = 0

        owner_name = tenant.get("owner_name") or "there"
        biz_name = tenant.get("business_name") or "Your Business"
        biz_type = tenant.get("business_type") or "local business"

        # Generate AI insights
        ai_insights = ""
        try:
            prompt = f"""You are a business intelligence analyst for a {biz_type} called "{biz_name}".

Here are this week's metrics:
- New leads: {metrics.get("new_leads", 0)} (hot: {metrics.get("hot_leads", 0)})
- Conversations: {metrics.get("conversations", 0)}
- Appointments booked: {metrics.get("appointments", 0)}
- Invoices sent: {metrics.get("invoices_sent", 0)}, paid: {metrics.get("invoices_paid", 0)}
- Revenue collected: ${metrics.get("revenue_collected", 0):.2f}
- Pipeline value (new leads): ${metrics.get("total_deal_value", 0):.2f}
- New reviews: {metrics.get("new_reviews", 0)} (avg rating: {metrics.get("avg_rating", 0)})
- Pending action items: {metrics.get("pending_actions", 0)}

Write a brief, actionable weekly intelligence summary (3-5 bullet points). Focus on:
1. What went well this week
2. What needs attention (missed opportunities, overdue items)
3. One specific recommendation to improve next week

Keep it concise, professional, and encouraging. Use actual numbers. No fluff."""

            response = call_claude_messages_sync(
                operation="automation.weekly_intelligence_brief",
                model="claude-sonnet-4-6",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
                timeout=30.0,
                max_retries=1,
                retry_delay_seconds=0.75,
                metadata={
                    "tenant_id": tid,
                    "business_type": biz_type,
                    "new_leads": metrics.get("new_leads", 0),
                    "conversations": metrics.get("conversations", 0),
                    "appointments": metrics.get("appointments", 0),
                    "revenue_collected": metrics.get("revenue_collected", 0),
                    "pending_actions": metrics.get("pending_actions", 0),
                },
            )
            ai_insights = response.text
        except Exception:
            logger.warning(
                "weekly brief: AI analysis failed for tenant %s", tid, exc_info=True
            )

        # Build email
        insights_html = ""
        if ai_insights:
            # Convert markdown-ish bullet points to HTML
            lines = ai_insights.strip().split("\n")
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    formatted_lines.append(
                        f"<li style='margin-bottom:8px;color:#374151;'>{line[2:]}</li>"
                    )
                elif line:
                    formatted_lines.append(f"<p style='color:#374151;'>{line}</p>")
            insights_html = (
                "<ul style='padding-left:20px;'>" + "".join(formatted_lines) + "</ul>"
            )

        subject = f"Weekly Intelligence Brief — {biz_name}"
        body_html = (
            f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
            f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
            f"<p style='color:#374151;'>Here's your weekly business intelligence brief for <strong>{biz_name}</strong>.</p>"
            f"<h3 style='color:#1e293b;margin-top:24px;'>This Week's Numbers</h3>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;'>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>New Leads</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('new_leads', 0)} ({metrics.get('hot_leads', 0)} hot)</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Conversations</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('conversations', 0)}</td></tr>"
            f"<tr style='background:#f3f4f6;'><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Appointments</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('appointments', 0)}</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Revenue Collected</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;font-weight:bold;color:#059669;'>${metrics.get('revenue_collected', 0):,.2f}</td></tr>"
            f"<tr style='background:#f3f4f6;'><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Reviews</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('new_reviews', 0)} (avg {metrics.get('avg_rating', 0)})</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Pending Actions</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('pending_actions', 0)}</td></tr>"
            f"</table>"
        )
        if insights_html:
            body_html += (
                f"<h3 style='color:#1e293b;margin-top:24px;'>AI Insights</h3>"
                f"{insights_html}"
            )
        body_html += (
            f"<p style='margin-top:24px;color:#374151;'>View your full dashboard at "
            f"<a href='https://app.agentnexlify.com' style='color:#3b82f6;'>app.agentnexlify.com</a></p>"
            f"<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p></div>"
        )

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body_html, tenant_id=tid
            )
            if result.get("success"):
                sent += 1
                logger.info(
                    "Sent weekly intelligence brief to %s (tenant %s)", email, tid
                )
                # Track in activity_log for dedup
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tid,
                    activity_type=week_tag,
                    description=f"Weekly intelligence brief sent: {metrics.get('new_leads', 0)} leads, ${metrics.get('revenue_collected', 0):.2f} revenue",
                )
        except Exception:
            logger.exception(
                "Failed to send weekly brief to %s (tenant %s)", email, tid
            )

    return sent


# ---------------------------------------------------------------------------
# Weekly digest — chatbot performance stats for paid tenants (Fridays)
# ---------------------------------------------------------------------------


async def send_weekly_digest() -> int:
    """Send a weekly chatbot performance digest email to paid tenants.

    Runs in the automation loop (30-min tier). Only executes on Fridays
    (weekday == 4). Gathers 7-day chat metrics and emails a branded
    summary to each tenant. Deduped via activity_log.

    Returns count of emails sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    # Only run on Fridays (weekday() == 4)
    if now.weekday() != 4:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_digest_{now.date().isoformat()}"
    sent = 0

    # Fetch paid tenants (not free plan)
    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .neq("plan", "free")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_weekly_digest: failed to query tenants")
        return 0

    for tenant in tenants.data or []:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        # Dedup — one digest per tenant per week
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("activity_type", week_tag)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning("send_weekly_digest: dedup check failed for tenant %s", tid)
            continue

        # ---- Gather 7-day chatbot metrics ----

        # Total conversations (distinct session_ids) and total messages
        conversations = 0
        messages = 0
        try:
            msgs_result = (
                db.table("chat_messages")
                .select("session_id")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(5000)
                .execute()
            )
            msgs_data = msgs_result.data or []
            messages = len(msgs_data)
            conversations = len(
                {m["session_id"] for m in msgs_data if m.get("session_id")}
            )
        except Exception:
            logger.warning(
                "send_weekly_digest: failed to count messages for tenant %s",
                tid,
                exc_info=True,
            )

        # Leads captured (uses client_id, NOT tenant_id)
        leads_count = 0
        try:
            leads_result = (
                db.table("leads")
                .select("id", count="exact")
                .eq("client_id", tid)
                .gte("created_at", week_start)
                .limit(1)
                .execute()
            )
            leads_count = leads_result.count or 0
        except Exception:
            logger.warning(
                "send_weekly_digest: failed to count leads for tenant %s",
                tid,
                exc_info=True,
            )

        # Top question — most common user message (exclude greetings / single chars)
        top_question = "N/A"
        try:
            user_msgs = (
                db.table("chat_messages")
                .select("content")
                .eq("tenant_id", tid)
                .eq("role", "user")
                .gte("created_at", week_start)
                .limit(500)
                .execute()
            )
            skip_words = {
                "hi",
                "hello",
                "hey",
                "e",
                "ok",
                "yes",
                "no",
                "thanks",
                "thank you",
            }
            freq: dict[str, int] = {}
            for m in user_msgs.data or []:
                content = (m.get("content") or "").strip()
                if not content or len(content) <= 2:
                    continue
                if content.lower() in skip_words:
                    continue
                key = content[:120]  # Normalize long messages
                freq[key] = freq.get(key, 0) + 1
            if freq:
                top_question = max(freq, key=freq.get)  # type: ignore[arg-type]
        except Exception:
            logger.warning(
                "send_weekly_digest: failed to find top question for tenant %s",
                tid,
                exc_info=True,
            )

        # ---- Build branded HTML email ----
        owner_name = tenant.get("owner_name") or "there"
        biz_name = tenant.get("business_name") or "Your Business"

        subject = f"Your weekly chat report — {biz_name}"

        # Truncate top_question for display
        display_question = (
            top_question if len(top_question) <= 80 else top_question[:77] + "..."
        )

        body_html = (
            f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
            f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
            f"<p style='color:#374151;'>Here's how your AI assistant performed this week:</p>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;"
            f"background:#1e293b;border-radius:8px;overflow:hidden;'>"
            f"<tr style='border-bottom:1px solid #334155;'>"
            f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Conversations</td>"
            f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{conversations}</td></tr>"
            f"<tr style='border-bottom:1px solid #334155;'>"
            f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Messages</td>"
            f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{messages}</td></tr>"
            f"<tr style='border-bottom:1px solid #334155;'>"
            f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Leads Captured</td>"
            f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{leads_count}</td></tr>"
            f"<tr>"
            f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Top Question</td>"
            f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-style:italic;'>"
            f"&ldquo;{display_question}&rdquo;</td></tr>"
            f"</table>"
            f"<p style='margin-top:24px;'>"
            f"<a href='https://app.agentnexlify.com/analytics' "
            f"style='color:#3b82f6;font-weight:600;text-decoration:none;'>View full analytics &rarr;</a></p>"
            f"<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p>"
            f"</div>"
        )

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body_html, tenant_id=tid
            )
            if result.get("success"):
                sent += 1
                logger.info("Sent weekly digest to %s (tenant %s)", email, tid)
                # Track in activity_log for dedup
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tid,
                    activity_type=week_tag,
                    description=f"Weekly digest sent: {conversations} conversations, {messages} messages, {leads_count} leads",
                )
        except Exception:
            logger.exception(
                "Failed to send weekly digest to %s (tenant %s)", email, tid
            )

    return sent


# ---------------------------------------------------------------------------
# Birthday automation — send birthday greetings to leads
# ---------------------------------------------------------------------------


async def send_birthday_greetings() -> int:
    """Check for leads with birthdays today and send greeting emails.

    Deduped via activity_log (birthday_greeting_{year} per lead).
    Runs daily, checks all tenants with paid plans.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    today_mmdd = now.strftime("%m-%d")
    current_year = now.year
    sent = 0

    try:
        leads = (
            db.table("leads")
            .select("id, client_id, name, email, date_of_birth")
            .not_.is_("date_of_birth", "null")
            .not_.is_("email", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_birthday_greetings: failed to query leads")
        return 0

    birthday_leads = [
        lead
        for lead in (leads.data or [])
        if lead.get("date_of_birth", "")[5:10] == today_mmdd
    ]

    if not birthday_leads:
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for lead in birthday_leads:
        tenant_id = lead["client_id"]
        lead_id = lead["id"]

        # Dedup: check if already sent this year
        try:
            tag = f"birthday_greeting_{current_year}"
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", lead_id)
                .eq("activity_type", tag)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in sequence enrollment", exc_info=True)

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant or (tenant.get("plan") or "free") == "free":
            continue

        business_name = tenant.get("business_name") or "Us"
        customer_name = lead.get("name") or "there"

        subject = f"Happy Birthday from {business_name}!"
        body = (
            f"<h2>Happy Birthday, {customer_name}!</h2>"
            f"<p>Everyone at <strong>{business_name}</strong> wishes you a wonderful birthday!</p>"
            f"<p>As a special thank you for being a valued client, we'd love to see you soon. "
            f"Reply to this email or contact us to schedule your next visit.</p>"
            f"<p>Best wishes,<br>The {business_name} Team</p>"
        )

        try:
            result = await send_email(
                to=lead["email"], subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
        except Exception:
            logger.exception("Failed to send birthday greeting to lead %s", lead_id)

        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "activity_type": f"birthday_greeting_{current_year}",
                    "description": f"Birthday greeting sent to {customer_name}",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log birthday greeting for lead %s", lead_id, exc_info=True
            )

    return sent


async def process_recurring_invoices() -> int:
    """Create new invoices from recurring invoices whose next_invoice_date has arrived.

    Runs every 30 min in the automation loop. For each recurring invoice with
    next_invoice_date <= today:
    1. Create a new draft invoice with the same line items
    2. Advance the parent's next_invoice_date by the recurrence_interval
    3. Log the activity
    """
    from datetime import date

    db = get_service_supabase()
    today_str = date.today().isoformat()

    try:
        due = (
            db.table("invoices")
            .select(
                "id, tenant_id, lead_id, items_json, tax_rate, notes, recurrence_interval, next_invoice_date, invoice_number"
            )
            .eq("is_recurring", True)
            .lte("next_invoice_date", today_str)
            .not_.is_("next_invoice_date", "null")
            .neq("status", "cancelled")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("process_recurring_invoices: query failed")
        return 0

    if not due.data:
        return 0

    created = 0
    for parent in due.data:
        parent_id = parent["id"]
        tenant_id = parent["tenant_id"]
        try:
            items = parent.get("items_json") or []
            tax_rate = float(parent.get("tax_rate") or 0)
            subtotal = sum(
                float(i.get("quantity", 1)) * float(i.get("unit_price", 0))
                for i in items
            )
            tax_amount = round(subtotal * tax_rate / 100, 2)
            total = round(subtotal + tax_amount, 2)

            # Generate invoice number
            prefix = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            count_result = (
                db.table("invoices")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .execute()
            )
            seq = (count_result.count or 0) + 1
            invoice_number = f"{prefix}-{seq:04d}"

            # Calculate due date (same offset as recurrence interval)
            from dateutil.relativedelta import relativedelta

            interval = parent.get("recurrence_interval", "monthly")
            intervals_map = {
                "weekly": relativedelta(weeks=1),
                "biweekly": relativedelta(weeks=2),
                "monthly": relativedelta(months=1),
                "quarterly": relativedelta(months=3),
            }
            delta = intervals_map.get(interval, relativedelta(months=1))
            due_date = (date.today() + delta).isoformat()
            original_next_date = parent["next_invoice_date"]
            next_date = date.fromisoformat(original_next_date) + delta

            # Claim the recurring parent row before inserting the child invoice.
            # This keeps multiple workers from generating the same invoice twice.
            claim_result = (
                db.table("invoices")
                .update(
                    {
                        "next_invoice_date": next_date.isoformat(),
                    }
                )
                .eq("id", parent_id)
                .eq("next_invoice_date", original_next_date)
                .select("id")
                .execute()
            )
            if not claim_result.data:
                logger.info(
                    "Skipping recurring invoice %s because another worker already claimed it",
                    parent_id,
                )
                continue

            new_invoice = {
                "tenant_id": tenant_id,
                "lead_id": parent.get("lead_id"),
                "parent_invoice_id": parent_id,
                "invoice_number": invoice_number,
                "items_json": items,
                "subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "notes": parent.get("notes"),
                "status": "draft",
                "due_date": due_date,
                "is_recurring": False,  # child is not itself recurring
            }
            try:
                insert_result = db.table("invoices").insert(new_invoice).execute()
            except Exception:
                # Best-effort rollback so the parent can be retried on the next tick.
                try:
                    db.table("invoices").update(
                        {
                            "next_invoice_date": original_next_date,
                        }
                    ).eq("id", parent_id).eq(
                        "next_invoice_date", next_date.isoformat()
                    ).execute()
                except Exception:
                    logger.warning(
                        "Failed to roll back recurring invoice claim for %s",
                        parent_id,
                        exc_info=True,
                    )
                raise

            created_invoice = insert_result.data[0] if insert_result.data else {}

            created += 1
            logger.info(
                "Created recurring invoice %s from parent %s for tenant %s (next: %s)",
                invoice_number,
                parent_id,
                tenant_id,
                next_date.isoformat(),
            )

            try:
                fire_event_background(
                    tenant_id,
                    "invoice.created",
                    {
                        "invoice_id": created_invoice.get("id"),
                        "invoice_number": invoice_number,
                        "total": total,
                        "status": "draft",
                        "recurring_from": parent_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue invoice.created webhook for recurring invoice %s",
                    parent_id,
                )

        except Exception:
            logger.exception("Failed to process recurring invoice %s", parent_id)

    return created


# ---------------------------------------------------------------------------
# Automation Rules — trigger evaluation and action execution
# ---------------------------------------------------------------------------


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
        from backend.routers.marketing_campaigns import _send_campaign_background

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
