"""Email Sequences endpoints — drip sequence builder with lead enrollment and send processing."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.email_sender import build_unsubscribe_url, render_template, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/email-sequences", tags=["email-sequences"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class StepCreate(BaseModel):
    step_order: int
    delay_days: int = 0
    delay_hours: int = 0
    subject: str
    body: str
    email_type: str = "email"
    is_active: bool = True


class StepUpdate(BaseModel):
    step_order: int | None = None
    delay_days: int | None = None
    delay_hours: int | None = None
    subject: str | None = None
    body: str | None = None
    email_type: str | None = None
    is_active: bool | None = None


class SequenceCreate(BaseModel):
    name: str
    trigger_type: str = "lead_captured"
    trigger_config: dict = {}
    is_active: bool = True
    steps: list[StepCreate] = []


class SequenceUpdate(BaseModel):
    name: str | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    is_active: bool | None = None
    steps: list[StepCreate] | None = None  # if provided, replaces all steps


class EnrollRequest(BaseModel):
    lead_id: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enroll_lead(
    db,
    sequence_id: str,
    sequence_steps: list[dict],
    lead_id: str,
    tenant_id: str,
) -> str | None:
    """Enroll a lead in a sequence and schedule all active steps.

    Uses ON CONFLICT DO NOTHING to silently skip duplicate enrollments.
    Returns the enrollment_id, or None if already enrolled (conflict).
    """
    now = datetime.now(timezone.utc)

    # Upsert enrollment — ON CONFLICT DO NOTHING via ignore_duplicates
    try:
        enroll_result = (
            db.table("email_sequence_enrollments")
            .upsert(
                {
                    "sequence_id": sequence_id,
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "status": "active",
                    "current_step": 0,
                    "enrolled_at": now.isoformat(),
                },
                on_conflict="sequence_id,lead_id",
                ignore_duplicates=True,
            )
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to upsert enrollment for lead %s in sequence %s", lead_id, sequence_id
        )
        return None

    if not enroll_result.data:
        # Conflict — lead already enrolled, fetch existing enrollment id
        try:
            existing = (
                db.table("email_sequence_enrollments")
                .select("id")
                .eq("sequence_id", sequence_id)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.info(
                    "Lead %s already enrolled in sequence %s (enrollment %s)",
                    lead_id, sequence_id, existing.data[0]["id"],
                )
                return existing.data[0]["id"]
        except Exception:
            logger.exception("Failed to fetch existing enrollment for lead %s", lead_id)
        return None

    enrollment_id = enroll_result.data[0]["id"]

    # Schedule a send record for each active step
    active_steps = [s for s in sequence_steps if s.get("is_active", True)]
    for step in active_steps:
        scheduled_for = now + timedelta(
            days=step.get("delay_days", 0),
            hours=step.get("delay_hours", 0),
        )
        try:
            db.table("email_sequence_sends").insert({
                "enrollment_id": enrollment_id,
                "step_id": step["id"],
                "lead_id": lead_id,
                "tenant_id": tenant_id,
                "status": "pending",
                "scheduled_for": scheduled_for.isoformat(),
            }).execute()
        except Exception:
            logger.exception(
                "Failed to schedule send for step %s (enrollment %s)", step["id"], enrollment_id
            )

    logger.info(
        "Enrolled lead %s in sequence %s — enrollment %s, %d steps scheduled",
        lead_id, sequence_id, enrollment_id, len(active_steps),
    )
    return enrollment_id


async def enroll_lead_in_sequences(tenant_id: str, lead_id: str) -> None:
    """Enroll a lead in all active 'lead_captured' sequences for this tenant.

    Called from widget_lead.py on new lead creation.
    """
    db = get_service_supabase()
    try:
        sequences_result = (
            db.table("email_sequences")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("trigger_type", "lead_captured")
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to query lead_captured sequences for tenant %s", tenant_id
        )
        return

    sequences = sequences_result.data or []
    if not sequences:
        return

    for seq in sequences:
        sequence_id = seq["id"]
        try:
            steps_result = (
                db.table("email_sequence_steps")
                .select("*")
                .eq("sequence_id", sequence_id)
                .order("step_order")
                .execute()
            )
            steps = steps_result.data or []
            _enroll_lead(db, sequence_id, steps, lead_id, tenant_id)
        except Exception:
            logger.exception(
                "Failed to enroll lead %s in sequence %s", lead_id, sequence_id
            )


# ---------------------------------------------------------------------------
# CRUD — Sequences
# ---------------------------------------------------------------------------

@router.get("")
async def list_sequences(
    claims: dict = Depends(_get_current_tenant),
):
    """List all email sequences for the tenant with step_count and enrollment_count."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    try:
        result = (
            db.table("email_sequences")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        sequences = result.data or []
    except Exception:
        logger.exception("Failed to list email sequences for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list sequences")

    # Enrich each sequence with step_count and enrollment_count
    enriched = []
    for seq in sequences:
        seq_id = seq["id"]

        try:
            step_count_res = (
                db.table("email_sequence_steps")
                .select("id", count="exact")
                .eq("sequence_id", seq_id)
                .execute()
            )
            seq["step_count"] = step_count_res.count if step_count_res.count is not None else 0
        except Exception:
            logger.warning("Failed to fetch step count for sequence %s", seq_id, exc_info=True)
            seq["step_count"] = 0

        try:
            enroll_count_res = (
                db.table("email_sequence_enrollments")
                .select("id", count="exact")
                .eq("sequence_id", seq_id)
                .execute()
            )
            seq["enrollment_count"] = enroll_count_res.count if enroll_count_res.count is not None else 0
        except Exception:
            logger.warning("Failed to fetch enrollment count for sequence %s", seq_id, exc_info=True)
            seq["enrollment_count"] = 0

        enriched.append(seq)

    return {"sequences": enriched, "total": len(enriched)}


@router.post("", status_code=201)
async def create_sequence(
    req: SequenceCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new email sequence, optionally with steps in the same request."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    try:
        seq_result = (
            db.table("email_sequences")
            .insert({
                "tenant_id": tenant_id,
                "name": req.name,
                "trigger_type": req.trigger_type,
                "trigger_config": req.trigger_config,
                "is_active": req.is_active,
            })
            .execute()
        )
        if not seq_result.data:
            raise HTTPException(status_code=500, detail="Failed to create sequence")
        sequence = seq_result.data[0]
        sequence_id = sequence["id"]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create email sequence for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create sequence")

    # Insert steps if provided
    created_steps = []
    for step in req.steps:
        try:
            step_result = (
                db.table("email_sequence_steps")
                .insert({
                    "sequence_id": sequence_id,
                    "step_order": step.step_order,
                    "delay_days": step.delay_days,
                    "delay_hours": step.delay_hours,
                    "subject": step.subject,
                    "body": step.body,
                    "email_type": step.email_type,
                    "is_active": step.is_active,
                })
                .execute()
            )
            if step_result.data:
                created_steps.append(step_result.data[0])
        except Exception:
            logger.exception(
                "Failed to create step %d for sequence %s", step.step_order, sequence_id
            )

    sequence["steps"] = created_steps
    return sequence


@router.get("/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single sequence with its steps and enrollment stats."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    try:
        seq_result = (
            db.table("email_sequences")
            .select("*")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
        sequence = seq_result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get sequence %s for tenant %s", sequence_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to get sequence")

    # Fetch steps
    try:
        steps_result = (
            db.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id)
            .order("step_order")
            .execute()
        )
        sequence["steps"] = steps_result.data or []
    except Exception:
        logger.warning("Failed to fetch steps for sequence %s", sequence_id, exc_info=True)
        sequence["steps"] = []

    # Enrollment stats
    try:
        stats_result = (
            db.table("email_sequence_enrollments")
            .select("status")
            .eq("sequence_id", sequence_id)
            .execute()
        )
        enrollments = stats_result.data or []
        by_status: dict[str, int] = {}
        for e in enrollments:
            s = e["status"]
            by_status[s] = by_status.get(s, 0) + 1
        sequence["enrollment_stats"] = {
            "total": len(enrollments),
            "by_status": by_status,
        }
    except Exception:
        logger.warning("Failed to fetch enrollment stats for sequence %s", sequence_id, exc_info=True)
        sequence["enrollment_stats"] = {"total": 0, "by_status": {}}

    return sequence


@router.put("/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    req: SequenceUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update sequence fields."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    raw = req.model_dump()
    new_steps = raw.pop("steps", None)
    updates = {k: v for k, v in raw.items() if v is not None}
    if not updates and new_steps is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        if updates:
            result = (
                db.table("email_sequences")
                .update(updates)
                .eq("id", sequence_id)
                .eq("tenant_id", tenant_id)
                .execute()
            )
            if not result.data:
                raise HTTPException(status_code=404, detail="Sequence not found")
            seq = result.data[0]
        else:
            # Verify ownership even if only steps are being updated
            seq_result = (
                db.table("email_sequences")
                .select("*")
                .eq("id", sequence_id)
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            if not seq_result.data:
                raise HTTPException(status_code=404, detail="Sequence not found")
            seq = seq_result.data[0]

        # Replace steps if provided
        if new_steps is not None:
            db.table("email_sequence_steps").delete().eq("sequence_id", sequence_id).execute()
            for s in new_steps:
                db.table("email_sequence_steps").insert({
                    "sequence_id": sequence_id,
                    "step_order": s["step_order"],
                    "delay_days": s.get("delay_days", 0),
                    "delay_hours": s.get("delay_hours", 0),
                    "subject": s["subject"],
                    "body": s["body"],
                    "email_type": s.get("email_type", "email"),
                    "is_active": s.get("is_active", True),
                }).execute()

        return seq
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update sequence %s for tenant %s", sequence_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update sequence")


@router.delete("/{sequence_id}", status_code=204)
async def delete_sequence(
    sequence_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Soft-delete a sequence by setting is_active=False."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    try:
        result = (
            db.table("email_sequences")
            .update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete sequence %s for tenant %s", sequence_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete sequence")


# ---------------------------------------------------------------------------
# CRUD — Steps
# ---------------------------------------------------------------------------

@router.post("/{sequence_id}/steps", status_code=201)
async def add_step(
    sequence_id: str,
    req: StepCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Add a step to a sequence."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    # Verify sequence ownership
    try:
        seq_check = (
            db.table("email_sequences")
            .select("id")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_check.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify sequence ownership %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to add step")

    try:
        result = (
            db.table("email_sequence_steps")
            .insert({
                "sequence_id": sequence_id,
                "step_order": req.step_order,
                "delay_days": req.delay_days,
                "delay_hours": req.delay_hours,
                "subject": req.subject,
                "body": req.body,
                "email_type": req.email_type,
                "is_active": req.is_active,
            })
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to add step")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add step to sequence %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to add step")


@router.put("/{sequence_id}/steps/{step_id}")
async def update_step(
    sequence_id: str,
    step_id: str,
    req: StepUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a step in a sequence."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    # Verify sequence ownership
    try:
        seq_check = (
            db.table("email_sequences")
            .select("id")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_check.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify sequence ownership %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to update step")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = (
            db.table("email_sequence_steps")
            .update(updates)
            .eq("id", step_id)
            .eq("sequence_id", sequence_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Step not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update step %s in sequence %s", step_id, sequence_id)
        raise HTTPException(status_code=500, detail="Failed to update step")


@router.delete("/{sequence_id}/steps/{step_id}", status_code=204)
async def delete_step(
    sequence_id: str,
    step_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a step from a sequence."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    # Verify sequence ownership
    try:
        seq_check = (
            db.table("email_sequences")
            .select("id")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_check.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify sequence ownership %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to delete step")

    try:
        result = (
            db.table("email_sequence_steps")
            .delete()
            .eq("id", step_id)
            .eq("sequence_id", sequence_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Step not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete step %s from sequence %s", step_id, sequence_id)
        raise HTTPException(status_code=500, detail="Failed to delete step")


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

@router.get("/{sequence_id}/enrollments")
async def list_enrollments(
    sequence_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List enrollments for a sequence with lead info."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    # Verify sequence ownership
    try:
        seq_check = (
            db.table("email_sequences")
            .select("id, name")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_check.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify sequence %s for tenant %s", sequence_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list enrollments")

    try:
        enroll_result = (
            db.table("email_sequence_enrollments")
            .select("*")
            .eq("sequence_id", sequence_id)
            .eq("tenant_id", tenant_id)
            .order("enrolled_at", desc=True)
            .execute()
        )
        enrollments = enroll_result.data or []
    except Exception:
        logger.exception("Failed to fetch enrollments for sequence %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to list enrollments")

    # Attach lead info (name, email)
    enriched = []
    for enrollment in enrollments:
        lead_id = enrollment["lead_id"]
        try:
            lead_result = (
                db.table("leads")
                .select("id, name, email, phone, status")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
            enrollment["lead"] = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.warning("Failed to fetch lead %s for enrollment listing", lead_id, exc_info=True)
            enrollment["lead"] = None
        enriched.append(enrollment)

    return {"enrollments": enriched, "total": len(enriched)}


@router.post("/{sequence_id}/enroll")
async def enroll_lead(
    sequence_id: str,
    req: EnrollRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Manually enroll a lead in a sequence."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    # Verify sequence ownership and that it is active
    try:
        seq_result = (
            db.table("email_sequences")
            .select("id, name, is_active")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify sequence %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to enroll lead")

    # Verify lead belongs to this tenant (leads use client_id)
    try:
        lead_result = (
            db.table("leads")
            .select("id, name, email")
            .eq("id", req.lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not lead_result.data:
            raise HTTPException(status_code=404, detail="Lead not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to verify lead %s for tenant %s", req.lead_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to enroll lead")

    # Load steps
    try:
        steps_result = (
            db.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id)
            .order("step_order")
            .execute()
        )
        steps = steps_result.data or []
    except Exception:
        logger.exception("Failed to load steps for sequence %s", sequence_id)
        raise HTTPException(status_code=500, detail="Failed to enroll lead")

    enrollment_id = _enroll_lead(db, sequence_id, steps, req.lead_id, tenant_id)
    if enrollment_id is None:
        raise HTTPException(status_code=409, detail="Lead is already enrolled in this sequence")

    return {
        "enrollment_id": enrollment_id,
        "sequence_id": sequence_id,
        "lead_id": req.lead_id,
        "steps_scheduled": len([s for s in steps if s.get("is_active", True)]),
    }


# ---------------------------------------------------------------------------
# Internal: Sequence Processor
# ---------------------------------------------------------------------------

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
        raise HTTPException(status_code=500, detail="Failed to query pending sends")

    processed = 0
    sent = 0
    failed = 0
    skipped = 0

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
                logger.warning("Step %s not found for send %s — skipping", step_id, send_id)
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
                logger.warning("Lead %s not found for send %s — skipping", lead_id, send_id)
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
            biz_row = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
            business_name = (biz_row.data[0].get("business_name") or "") if biz_row.data else ""
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
                _update_send_status(db, send_id, "sent", sent_at=datetime.now(timezone.utc).isoformat())
                sent += 1
                logger.info(
                    "Sent sequence email send=%s lead=%s step=%s",
                    send_id, lead_id, step_id,
                )
            else:
                err = result.get("detail", "send failed")
                _update_send_status(db, send_id, "failed", error=err)
                failed += 1
                logger.warning(
                    "Failed to send sequence email send=%s lead=%s: %s",
                    send_id, lead_id, err,
                )
        except Exception:
            logger.exception("Exception sending sequence email send=%s lead=%s", send_id, lead_id)
            _update_send_status(db, send_id, "failed", error="send exception")
            failed += 1
            continue

        # Check if this was the last step and mark enrollment completed
        try:
            _maybe_complete_enrollment(db, enrollment_id, step["sequence_id"])
        except Exception:
            logger.warning(
                "Failed to check enrollment completion for enrollment %s", enrollment_id, exc_info=True
            )

    return {
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }


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
    """Standalone callable for the automation loop (no HTTP context needed)."""
    db = get_service_supabase()
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
        logger.exception("run_sequence_processor: failed to query pending sends")
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    processed = sent = failed = skipped = 0
    for send_row in due_sends:
        send_id = send_row["id"]
        step_id = send_row["step_id"]
        lead_id = send_row["lead_id"]
        tenant_id = send_row["tenant_id"]
        enrollment_id = send_row["enrollment_id"]
        processed += 1
        try:
            step_result = db.table("email_sequence_steps").select("subject, body, email_type, step_order, sequence_id").eq("id", step_id).limit(1).execute()
            if not step_result.data:
                _update_send_status(db, send_id, "skipped", error="step not found")
                skipped += 1
                continue
            step = step_result.data[0]
        except Exception:
            _update_send_status(db, send_id, "failed", error="step load error")
            failed += 1
            continue
        try:
            lead_result = db.table("leads").select("id, name, email, unsubscribed").eq("id", lead_id).limit(1).execute()
            if not lead_result.data:
                _update_send_status(db, send_id, "skipped", error="lead not found")
                skipped += 1
                continue
            lead = lead_result.data[0]
        except Exception:
            _update_send_status(db, send_id, "failed", error="lead load error")
            failed += 1
            continue
        # CAN-SPAM: never send to unsubscribed leads
        if lead.get("unsubscribed"):
            _update_send_status(db, send_id, "skipped", error="unsubscribed")
            skipped += 1
            continue
        lead_email = lead.get("email", "")
        if not lead_email:
            _update_send_status(db, send_id, "skipped", error="no email address")
            skipped += 1
            continue
        try:
            biz_row = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
            _biz = (biz_row.data[0].get("business_name") or "") if biz_row.data else ""
        except Exception:
            _biz = ""
        _ctx = {"name": lead.get("name") or "there", "email": lead_email, "business_name": _biz}
        try:
            result = await send_email(
                to=lead_email,
                subject=render_template(step["subject"], _ctx),
                body_html=render_template(step["body"], _ctx),
                tenant_id=tenant_id,
                unsubscribe_url=build_unsubscribe_url(lead_id, tenant_id),
                lead_id=lead_id,
            )
            if result.get("success"):
                _update_send_status(db, send_id, "sent", sent_at=datetime.now(timezone.utc).isoformat())
                sent += 1
            else:
                _update_send_status(db, send_id, "failed", error=result.get("detail", "send failed"))
                failed += 1
        except Exception:
            logger.exception("run_sequence_processor: exception sending send=%s", send_id)
            _update_send_status(db, send_id, "failed", error="send exception")
            failed += 1
            continue
        try:
            _maybe_complete_enrollment(db, enrollment_id, step["sequence_id"])
        except Exception:
            logger.warning("run_sequence_processor: completion check failed for enrollment %s", enrollment_id, exc_info=True)

    if processed:
        logger.info("run_sequence_processor: processed=%d sent=%d failed=%d skipped=%d", processed, sent, failed, skipped)
    return {"processed": processed, "sent": sent, "failed": failed, "skipped": skipped}


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
            db.table("email_sequence_enrollments").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", enrollment_id).execute()
            logger.info("Enrollment %s marked as completed", enrollment_id)
    except Exception:
        logger.exception("Failed to complete enrollment %s", enrollment_id)
