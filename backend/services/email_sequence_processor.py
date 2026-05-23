"""Email-sequence send processor — shared core for HTTP endpoint + standalone caller.

Extracted from ``backend/routers/email_sequences.py`` to (1) deduplicate the
HTTP route handler and the cron-callable, and (2) move processor logic out of
the router so it can be tested directly.

Public:
- ``process_due_sends(db)`` — run one batch of pending sends; returns counts.
- ``run_sequence_processor()`` — standalone callable for the automation loop.
- ``increment_runs_total(tenant_id, automation_type)`` — bump automations.runs_total.

Internals:
- ``_process_one_send(db, send_row)`` — handle a single email_sequence_sends row.
- ``_update_send_status(db, send_id, status, ...)`` — patch send row status.
- ``_maybe_complete_enrollment(db, enrollment_id, sequence_id)`` — flip
  enrollment to ``completed`` when no pending sends remain.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.email_sender import (
    build_unsubscribe_url,
    render_template,
    send_email,
)

logger = logging.getLogger(__name__)


def increment_runs_total(tenant_id: str, automation_type: str) -> None:
    """Increment automations.runs_total for (tenant_id, type). Silently swallows errors."""
    try:
        db = get_service_supabase()
        result = (
            db.table("automations")
            .select("id, runs_total")
            .eq("tenant_id", tenant_id)
            .eq("type", automation_type)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            db.table("automations").update({"runs_total": row["runs_total"] + 1}).eq(
                "id", row["id"]
            ).execute()
    except Exception:
        logger.warning(
            "Failed to increment runs_total tenant=%s type=%s",
            tenant_id,
            automation_type,
            exc_info=True,
        )


def _update_send_status(
    db,
    send_id: str,
    status: str,
    error: str = "",
    sent_at: str = "",
) -> None:
    """Helper to update an email_sequence_sends row status."""
    updates: dict = {"status": status}
    if error:
        updates["error"] = error
    if sent_at:
        updates["sent_at"] = sent_at
    try:
        db.table("email_sequence_sends").update(updates).eq("id", send_id).execute()
    except Exception:
        logger.exception("Failed to update send status for send %s", send_id)


def _maybe_complete_enrollment(db, enrollment_id: str, sequence_id: str) -> None:
    """Mark an enrollment as completed when no pending sends remain."""
    try:
        remaining = (
            db.table("email_sequence_sends")
            .select("id", count="exact")
            .eq("enrollment_id", enrollment_id)
            .eq("status", "pending")
            .execute()
        )
        pending_count = remaining.count if remaining.count is not None else 0
        if pending_count == 0:
            db.table("email_sequence_enrollments").update(
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", enrollment_id).execute()
            logger.info("Enrollment %s marked as completed", enrollment_id)
    except Exception:
        logger.exception("Failed to complete enrollment %s", enrollment_id)


async def _process_one_send(db, send_row: dict) -> str:
    """Process a single send row. Returns 'sent', 'failed', or 'skipped'."""
    send_id = send_row["id"]
    step_id = send_row["step_id"]
    lead_id = send_row["lead_id"]
    tenant_id = send_row["tenant_id"]
    enrollment_id = send_row["enrollment_id"]

    # Load step
    try:
        step_result = (
            db.table("email_sequence_steps")
            .select("subject, body, email_type, step_order, sequence_id")
            .eq("id", step_id)
            .limit(1)
            .execute()
        )
        if not step_result.data:
            logger.warning(
                "Step %s not found for send %s — skipping", step_id, send_id
            )
            _update_send_status(db, send_id, "skipped", error="step not found")
            return "skipped"
        step = step_result.data[0]
    except Exception:
        logger.exception("Failed to load step %s for send %s", step_id, send_id)
        _update_send_status(db, send_id, "failed", error="step load error")
        return "failed"

    # Load lead
    try:
        lead_result = (
            db.table("leads")
            .select("id, name, email, unsubscribed")
            .eq("id", lead_id)
            .limit(1)
            .execute()
        )
        if not lead_result.data:
            logger.warning(
                "Lead %s not found for send %s — skipping", lead_id, send_id
            )
            _update_send_status(db, send_id, "skipped", error="lead not found")
            return "skipped"
        lead = lead_result.data[0]
    except Exception:
        logger.exception("Failed to load lead %s for send %s", lead_id, send_id)
        _update_send_status(db, send_id, "failed", error="lead load error")
        return "failed"

    # CAN-SPAM: never send to unsubscribed leads
    if lead.get("unsubscribed"):
        logger.info("Lead %s is unsubscribed, skipping send %s", lead_id, send_id)
        _update_send_status(db, send_id, "skipped", error="unsubscribed")
        return "skipped"

    lead_email = lead.get("email", "")
    if not lead_email:
        logger.info("Lead %s has no email, skipping send %s", lead_id, send_id)
        _update_send_status(db, send_id, "skipped", error="no email address")
        return "skipped"

    # Render template variables before sending
    try:
        biz_row = (
            db.table("tenants")
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        business_name = (
            (biz_row.data[0].get("business_name") or "") if biz_row.data else ""
        )
    except Exception:
        business_name = ""

    ctx = {
        "name": lead.get("name") or "there",
        "email": lead_email,
        "business_name": business_name,
    }

    # Send the email
    try:
        unsub_url = build_unsubscribe_url(lead_id, tenant_id)
        result = await send_email(
            to=lead_email,
            subject=render_template(step["subject"], ctx),
            body_html=render_template(step["body"], ctx),
            tenant_id=tenant_id,
            unsubscribe_url=unsub_url,
            lead_id=lead_id,
        )
        if result.get("success"):
            _update_send_status(
                db, send_id, "sent", sent_at=datetime.now(timezone.utc).isoformat()
            )
            logger.info(
                "Sent sequence email send=%s lead=%s step=%s",
                send_id,
                lead_id,
                step_id,
            )
            log_activity(
                tenant_id=tenant_id,
                activity_type="email_sequence_sent",
                description=(
                    f"Follow-up email sent to {lead.get('name') or lead_email}"
                ),
                lead_id=lead_id,
                metadata={
                    "send_id": send_id,
                    "step_id": step_id,
                    "step_order": step.get("step_order"),
                    "sequence_id": step.get("sequence_id"),
                    "enrollment_id": enrollment_id,
                },
            )
            increment_runs_total(tenant_id, "email_sequence")
            outcome = "sent"
        else:
            err = result.get("detail", "send failed")
            _update_send_status(db, send_id, "failed", error=err)
            logger.warning(
                "Failed to send sequence email send=%s lead=%s: %s",
                send_id,
                lead_id,
                err,
            )
            outcome = "failed"
    except Exception:
        logger.exception(
            "Exception sending sequence email send=%s lead=%s", send_id, lead_id
        )
        _update_send_status(db, send_id, "failed", error="send exception")
        return "failed"

    # Check if this was the last step and mark enrollment completed
    try:
        _maybe_complete_enrollment(db, enrollment_id, step["sequence_id"])
    except Exception:
        logger.warning(
            "Failed to check enrollment completion for enrollment %s",
            enrollment_id,
            exc_info=True,
        )

    return outcome


async def process_due_sends(db) -> dict:
    """Process all pending email_sequence_sends whose scheduled_for <= now()."""
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        due_result = (
            db.table("email_sequence_sends")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now_iso)
            .limit(200)
            .execute()
        )
        due_sends = due_result.data or []
    except Exception:
        logger.exception("Failed to query pending email sequence sends")
        raise

    counts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    for send_row in due_sends:
        counts["processed"] += 1
        outcome = await _process_one_send(db, send_row)
        counts[outcome] += 1
    return counts


async def run_sequence_processor() -> dict:
    """Standalone callable for the automation loop (no HTTP context needed)."""
    db = get_service_supabase()
    try:
        counts = await process_due_sends(db)
    except Exception:
        logger.exception("run_sequence_processor: failed to query pending sends")
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    if counts["processed"]:
        logger.info(
            "run_sequence_processor: processed=%d sent=%d failed=%d skipped=%d",
            counts["processed"],
            counts["sent"],
            counts["failed"],
            counts["skipped"],
        )
    return counts
