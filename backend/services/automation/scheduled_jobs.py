"""Automation scheduled jobs — all send_* and check_* scheduled functions."""

import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import (
    build_unsubscribe_url,
    render_template,
    send_email,
)
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background
from backend.services.automation.templates import (
    _REMINDER_EXTRAS,
    _REBOOK_INTERVALS,
    _AFTERCARE_TEMPLATES,
    _ONBOARDING_STEPS,
)
from backend.services.automation.trigger import BATCH_LIMIT, trigger_sequence

logger = logging.getLogger(__name__)


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

    # Evaluate each lead in Python and collect (tenant_id, lead_id) pairs to trigger.
    # No DB calls here — all guard data was fetched in Q1-Q4 above.
    leads_to_trigger: list[tuple[str, str]] = []
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

        leads_to_trigger.append((tenant_id, lead_id))

    if not leads_to_trigger:
        return 0

    # Batch-trigger phase: group leads by tenant so we make ONE sequences query
    # and ONE steps query per tenant, then ONE bulk insert per tenant.
    # Before this change: O(3 * leads) DB round-trips.
    # After this change: O(3 * tenants) DB round-trips (tenants << leads in practice).

    leads_by_tenant: dict[str, list[str]] = defaultdict(list)
    for tenant_id, lead_id in leads_to_trigger:
        leads_by_tenant[tenant_id].append(lead_id)

    for tenant_id, lead_ids in leads_by_tenant.items():
        # Fetch active no_response_24h sequences for this tenant (1 query)
        try:
            seq_result = (
                tenant_table(db, "automation_sequences", tenant_id)
                .select("id, trigger_config")
                .eq("trigger_event", "no_response_24h")
                .eq("is_active", True)
                .execute()
            )
        except Exception:
            logger.exception(
                "check_no_response_leads: sequences query failed for tenant %s", tenant_id
            )
            continue

        sequences = seq_result.data or []
        if not sequences:
            continue

        # Fetch first active step for each sequence (1 query per tenant)
        seq_ids = [s["id"] for s in sequences]
        try:
            steps_result = (
                db.table("automation_steps")
                .select("sequence_id, step_order, delay_minutes")
                .in_("sequence_id", seq_ids)
                .eq("is_active", True)
                .order("step_order")
                .limit(len(seq_ids) * 20)
                .execute()
            )
        except Exception:
            logger.exception(
                "check_no_response_leads: steps query failed for tenant %s", tenant_id
            )
            continue

        first_step_by_seq: dict[str, dict] = {}
        for step in steps_result.data or []:
            sid = step["sequence_id"]
            if sid not in first_step_by_seq:
                first_step_by_seq[sid] = step

        # Build bulk enrollment records for all leads x all eligible sequences
        now_utc = datetime.now(timezone.utc)
        enrollment_records: list[dict] = []
        for seq in sequences:
            first_step = first_step_by_seq.get(seq["id"])
            if not first_step:
                continue
            next_run = now_utc + timedelta(minutes=first_step["delay_minutes"])
            for lead_id in lead_ids:
                enrollment_records.append(
                    {
                        "sequence_id": seq["id"],
                        "lead_id": lead_id,
                        "tenant_id": tenant_id,
                        "current_step": 1,
                        "status": "in_progress",
                        "next_run_at": next_run.isoformat(),
                    }
                )

        if not enrollment_records:
            continue

        # Single bulk insert for all (lead, sequence) pairs in this tenant
        try:
            tenant_table(db, "automation_executions", tenant_id).insert(
                enrollment_records
            ).execute()
            triggered += len(enrollment_records)
            logger.info(
                "check_no_response_leads: bulk enrolled %d executions for tenant %s "
                "(leads: %s)",
                len(enrollment_records),
                tenant_id,
                lead_ids,
            )
        except Exception as _bulk_exc:
            err_str = str(_bulk_exc).lower()
            if "unique" in err_str or "duplicate" in err_str:
                # Some leads already enrolled — fall back to per-record inserts
                logger.debug(
                    "check_no_response_leads: bulk insert hit unique constraint for tenant %s, "
                    "falling back to per-record inserts",
                    tenant_id,
                )
                for record in enrollment_records:
                    try:
                        tenant_table(db, "automation_executions", tenant_id).insert(
                            record
                        ).execute()
                        triggered += 1
                    except Exception as _rec_exc:
                        rec_err = str(_rec_exc).lower()
                        if "unique" in rec_err or "duplicate" in rec_err:
                            logger.debug(
                                "Lead %s already enrolled in sequence %s",
                                record["lead_id"],
                                record["sequence_id"],
                            )
                        else:
                            logger.warning(
                                "check_no_response_leads: failed to enroll lead %s in "
                                "sequence %s: %s",
                                record["lead_id"],
                                record["sequence_id"],
                                _rec_exc,
                                exc_info=True,
                            )
            else:
                logger.exception(
                    "check_no_response_leads: bulk insert failed for tenant %s", tenant_id
                )

    return triggered


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


# Re-export from scheduled_jobs_ext to keep the public API of this module intact
from backend.services.automation.scheduled_jobs_ext import (
    send_weekly_intelligence_briefs,
    send_weekly_digest,
    send_birthday_greetings,
    process_recurring_invoices,
)

__all__ = [
    "_get_reminder_extras",
    "check_no_response_leads",
    "send_appointment_reminders",
    "send_rebook_suggestions",
    "send_aftercare_instructions",
    "send_pending_review_requests",
    "_send_review_followups",
    "send_monthly_reports",
    "send_portal_links",
    "send_csat_surveys",
    "check_new_reviews",
    "send_onboarding_emails",
    "send_invoice_payment_reminders",
    "send_weekly_intelligence_briefs",
    "send_weekly_digest",
    "send_birthday_greetings",
    "process_recurring_invoices",
]
