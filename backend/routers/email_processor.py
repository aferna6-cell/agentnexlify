"""Email Sequences — send loop, scheduling, and processing.

Split from backend/routers/email_sequences.py (Rule 9 god-class split).
Sibling modules: email_crud.py (sequence/step CRUD),
email_enrollment.py (enroll/unenroll/enrollment state).

`run_sequence_processor` is the standalone callable used by the automation
loop in backend/main.py; `process_sequences` is the x-internal-key HTTP
entry point. Both delegate to `_process_pending_sends` (GH #113).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.email_sender import (
    build_unsubscribe_url,
    render_template,
    send_email,
)

logger = logging.getLogger(__name__)


def _increment_runs_total(tenant_id: str, automation_type: str) -> None:
    """Increment automations.runs_total for (tenant_id, type). Silently swallows errors.

    Mirrors twilio_webhooks._increment_runs_total. No-op when no automation row exists
    for the tenant — matches missed-call pattern.
    """
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


router = APIRouter(prefix="/api/v1/email-sequences", tags=["email-sequences"])


# ---------------------------------------------------------------------------
# Internal: Sequence Processor
# ---------------------------------------------------------------------------


async def _process_pending_sends(db, due_sends: list[dict]) -> dict:
    """Process a batch of due email-sequence sends. Shared by the HTTP endpoint
    (`process_sequences`) and the automation-loop callable
    (`run_sequence_processor`) so a fix to the per-send logic lands once (GH #113).

    Per send: load step -> load lead -> CAN-SPAM unsubscribe check -> render
    template -> send -> log activity + bump runs_total -> complete enrollment on
    the last step. Returns {processed, sent, failed, skipped}.
    """
    processed = sent = failed = skipped = 0

    for send_row in due_sends:
        send_id = send_row["id"]
        step_id = send_row["step_id"]
        lead_id = send_row["lead_id"]
        tenant_id = send_row["tenant_id"]
        enrollment_id = send_row["enrollment_id"]

        processed += 1

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
                skipped += 1
                continue
            step = step_result.data[0]
        except Exception:
            logger.exception("Failed to load step %s for send %s", step_id, send_id)
            _update_send_status(db, send_id, "failed", error="step load error")
            failed += 1
            continue

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
                skipped += 1
                continue
            lead = lead_result.data[0]
        except Exception:
            logger.exception("Failed to load lead %s for send %s", lead_id, send_id)
            _update_send_status(db, send_id, "failed", error="lead load error")
            failed += 1
            continue

        # CAN-SPAM: never send to unsubscribed leads
        if lead.get("unsubscribed"):
            logger.info("Lead %s is unsubscribed, skipping send %s", lead_id, send_id)
            _update_send_status(db, send_id, "skipped", error="unsubscribed")
            skipped += 1
            continue

        lead_email = lead.get("email", "")
        if not lead_email:
            logger.info("Lead %s has no email, skipping send %s", lead_id, send_id)
            _update_send_status(db, send_id, "skipped", error="no email address")
            skipped += 1
            continue

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
                sent += 1
                logger.info(
                    "Sent sequence email send=%s lead=%s step=%s",
                    send_id,
                    lead_id,
                    step_id,
                )
                log_activity(
                    tenant_id=tenant_id,
                    activity_type="email_sequence_sent",
                    description=f"Follow-up email sent to {lead.get('name') or lead_email}",
                    lead_id=lead_id,
                    metadata={
                        "send_id": send_id,
                        "step_id": step_id,
                        "step_order": step.get("step_order"),
                        "sequence_id": step.get("sequence_id"),
                        "enrollment_id": enrollment_id,
                    },
                )
                _increment_runs_total(tenant_id, "email_sequence")
            else:
                err = result.get("detail", "send failed")
                _update_send_status(db, send_id, "failed", error=err)
                failed += 1
                logger.warning(
                    "Failed to send sequence email send=%s lead=%s: %s",
                    send_id,
                    lead_id,
                    err,
                )
        except Exception:
            logger.exception(
                "Exception sending sequence email send=%s lead=%s", send_id, lead_id
            )
            _update_send_status(db, send_id, "failed", error="send exception")
            failed += 1
            continue

        # Check if this was the last step and mark enrollment completed
        try:
            _maybe_complete_enrollment(db, enrollment_id, step["sequence_id"])
        except Exception:
            logger.warning(
                "Failed to check enrollment completion for enrollment %s",
                enrollment_id,
                exc_info=True,
            )

    return {
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }


def _query_due_sends(db) -> list[dict]:
    """Fetch up to 200 pending sends whose scheduled_for has elapsed."""
    now_iso = datetime.now(timezone.utc).isoformat()
    due_result = (
        db.table("email_sequence_sends")
        .select("*")
        .eq("status", "pending")
        .lte("scheduled_for", now_iso)
        .limit(200)
        .execute()
    )
    return due_result.data or []


@router.post("/internal/process-sequences")
async def process_sequences(
    x_internal_key: str = Header(..., alias="x-internal-key"),
):
    """Process pending email sequence sends whose scheduled_for <= now().

    Protected by x-internal-key header. Intended to be called by the
    automation loop or an external cron job.
    """
    if x_internal_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    db = get_service_supabase()

    try:
        due_sends = _query_due_sends(db)
    except Exception:
        logger.exception("Failed to query pending email sequence sends")
        raise HTTPException(status_code=500, detail="Failed to query pending sends")

    return await _process_pending_sends(db, due_sends)


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


async def run_sequence_processor() -> dict:
    """Standalone callable for the automation loop (no HTTP context needed).

    Shares the per-send logic with the HTTP endpoint via
    ``_process_pending_sends`` (GH #113)."""
    db = get_service_supabase()
    try:
        due_sends = _query_due_sends(db)
    except Exception:
        logger.exception("run_sequence_processor: failed to query pending sends")
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    result = await _process_pending_sends(db, due_sends)

    if result["processed"]:
        logger.info(
            "run_sequence_processor: processed=%d sent=%d failed=%d skipped=%d",
            result["processed"],
            result["sent"],
            result["failed"],
            result["skipped"],
        )
    return result


def _maybe_complete_enrollment(db, enrollment_id: str, sequence_id: str) -> None:
    """Mark an enrollment as completed if all steps have been sent or skipped."""
    try:
        # Count sends that are still pending or being processed
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
