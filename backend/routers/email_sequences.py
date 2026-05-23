"""Email Sequences endpoints — drip sequence builder with lead enrollment and send processing.

Processor + enrollment cores live in:
- ``backend/services/email_sequence_processor.py``
- ``backend/services/email_sequence_enrollment.py``

This router stays focused on CRUD + HTTP wiring. The standalone callables
(``enroll_lead_in_sequences``, ``run_sequence_processor``) are re-exported so
existing imports from widget_lead, widget_lead_helpers, and main.py keep working.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.email_sequence_enrollment import (
    enroll_lead_in_sequence,
    enroll_lead_in_sequences,
)
from backend.services.email_sequence_processor import (
    process_due_sends,
    run_sequence_processor,
)

__all__ = ["router", "enroll_lead_in_sequences", "run_sequence_processor"]

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
            seq["step_count"] = (
                step_count_res.count if step_count_res.count is not None else 0
            )
        except Exception:
            logger.warning(
                "Failed to fetch step count for sequence %s", seq_id, exc_info=True
            )
            seq["step_count"] = 0

        try:
            enroll_count_res = (
                db.table("email_sequence_enrollments")
                .select("id", count="exact")
                .eq("sequence_id", seq_id)
                .execute()
            )
            seq["enrollment_count"] = (
                enroll_count_res.count if enroll_count_res.count is not None else 0
            )
        except Exception:
            logger.warning(
                "Failed to fetch enrollment count for sequence %s",
                seq_id,
                exc_info=True,
            )
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
            .insert(
                {
                    "tenant_id": tenant_id,
                    "name": req.name,
                    "trigger_type": req.trigger_type,
                    "trigger_config": req.trigger_config,
                    "is_active": req.is_active,
                }
            )
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
                .insert(
                    {
                        "sequence_id": sequence_id,
                        "step_order": step.step_order,
                        "delay_days": step.delay_days,
                        "delay_hours": step.delay_hours,
                        "subject": step.subject,
                        "body": step.body,
                        "email_type": step.email_type,
                        "is_active": step.is_active,
                    }
                )
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
        logger.exception(
            "Failed to get sequence %s for tenant %s", sequence_id, tenant_id
        )
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
        logger.warning(
            "Failed to fetch steps for sequence %s", sequence_id, exc_info=True
        )
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
        logger.warning(
            "Failed to fetch enrollment stats for sequence %s",
            sequence_id,
            exc_info=True,
        )
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
            db.table("email_sequence_steps").delete().eq(
                "sequence_id", sequence_id
            ).execute()
            for s in new_steps:
                db.table("email_sequence_steps").insert(
                    {
                        "sequence_id": sequence_id,
                        "step_order": s["step_order"],
                        "delay_days": s.get("delay_days", 0),
                        "delay_hours": s.get("delay_hours", 0),
                        "subject": s["subject"],
                        "body": s["body"],
                        "email_type": s.get("email_type", "email"),
                        "is_active": s.get("is_active", True),
                    }
                ).execute()

        return seq
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to update sequence %s for tenant %s", sequence_id, tenant_id
        )
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
            .update(
                {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to delete sequence %s for tenant %s", sequence_id, tenant_id
        )
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
            .insert(
                {
                    "sequence_id": sequence_id,
                    "step_order": req.step_order,
                    "delay_days": req.delay_days,
                    "delay_hours": req.delay_hours,
                    "subject": req.subject,
                    "body": req.body,
                    "email_type": req.email_type,
                    "is_active": req.is_active,
                }
            )
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
        logger.exception(
            "Failed to update step %s in sequence %s", step_id, sequence_id
        )
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
        logger.exception(
            "Failed to delete step %s from sequence %s", step_id, sequence_id
        )
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
        logger.exception(
            "Failed to verify sequence %s for tenant %s", sequence_id, tenant_id
        )
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
            logger.warning(
                "Failed to fetch lead %s for enrollment listing", lead_id, exc_info=True
            )
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
        logger.exception(
            "Failed to verify lead %s for tenant %s", req.lead_id, tenant_id
        )
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

    enrollment_id = enroll_lead_in_sequence(
        db, sequence_id, steps, req.lead_id, tenant_id
    )
    if enrollment_id is None:
        raise HTTPException(
            status_code=500, detail="Failed to enroll lead (database error)"
        )

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

    Protected by ``x-internal-key`` header. Intended to be called by the
    automation loop or an external cron job. All processing logic lives in
    ``backend.services.email_sequence_processor.process_due_sends``.
    """
    if x_internal_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    db = get_service_supabase()
    try:
        return await process_due_sends(db)
    except Exception:
        logger.exception("Failed to process due email sequence sends")
        raise HTTPException(status_code=500, detail="Failed to query pending sends")
