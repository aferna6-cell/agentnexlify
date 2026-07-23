"""Email Sequences — lead enrollment endpoints and enrollment helpers.

Split from backend/routers/email_sequences.py (Rule 9 god-class split).
Sibling modules: email_crud.py (sequence/step CRUD),
email_processor.py (send loop / scheduling / processing).

`enroll_lead_in_sequences` is the auto-enroll entry point called from
widget_lead.py / widget_lead_helpers.py on new lead creation.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/email-sequences", tags=["email-sequences"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


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
    Returns enrollment_id on success or on duplicate (existing id returned).
    Returns None only on database error.
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
            "Failed to upsert enrollment for lead %s in sequence %s",
            lead_id,
            sequence_id,
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
                    lead_id,
                    sequence_id,
                    existing.data[0]["id"],
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
            db.table("email_sequence_sends").insert(
                {
                    "enrollment_id": enrollment_id,
                    "step_id": step["id"],
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "status": "pending",
                    "scheduled_for": scheduled_for.isoformat(),
                }
            ).execute()
        except Exception:
            logger.exception(
                "Failed to schedule send for step %s (enrollment %s)",
                step["id"],
                enrollment_id,
            )

    logger.info(
        "Enrolled lead %s in sequence %s — enrollment %s, %d steps scheduled",
        lead_id,
        sequence_id,
        enrollment_id,
        len(active_steps),
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

    # Attach lead info (name, email) — one bulk query, not N+1 (GH #112).
    lead_ids = list({e["lead_id"] for e in enrollments if e.get("lead_id")})
    leads_by_id: dict[str, dict] = {}
    if lead_ids:
        try:
            leads_res = (
                db.table("leads")
                .select("id, name, email, phone, status")
                .in_("id", lead_ids)
                .execute()
            )
            leads_by_id = {row["id"]: row for row in (leads_res.data or [])}
        except Exception:
            logger.warning(
                "Failed to bulk-fetch leads for enrollment listing", exc_info=True
            )

    for enrollment in enrollments:
        enrollment["lead"] = leads_by_id.get(enrollment.get("lead_id"))

    return {"enrollments": enrollments, "total": len(enrollments)}


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

    enrollment_id = _enroll_lead(db, sequence_id, steps, req.lead_id, tenant_id)
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
