"""Enrollment-listing and manual-enrollment ops for the email-sequence router.

Distinct from ``email_sequence_enrollment.py``, which holds the core
``enroll_lead_in_sequence`` / ``enroll_lead_in_sequences`` callables shared with
``widget_lead.py``. This module is HTTP-tier glue: it raises ``HTTPException``
and is only imported by the router.
"""

import logging
from typing import Any

from fastapi import HTTPException

from backend.services.email_sequence_enrollment import enroll_lead_in_sequence

logger = logging.getLogger(__name__)

__all__ = [
    "list_enrollments_for_sequence",
    "manual_enroll_lead",
]


def _verify_sequence_for_listing(db: Any, tenant_id: str, sequence_id: str) -> None:
    """Raise 404 if sequence doesn't belong to tenant, 500 on DB error."""
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


def list_enrollments_for_sequence(
    db: Any, tenant_id: str, sequence_id: str
) -> dict:
    """Return enrollments for a sequence, with lead info attached."""
    _verify_sequence_for_listing(db, tenant_id, sequence_id)

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
        logger.exception(
            "Failed to fetch enrollments for sequence %s", sequence_id
        )
        raise HTTPException(status_code=500, detail="Failed to list enrollments")

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
                "Failed to fetch lead %s for enrollment listing",
                lead_id,
                exc_info=True,
            )
            enrollment["lead"] = None
        enriched.append(enrollment)

    return {"enrollments": enriched, "total": len(enriched)}


def manual_enroll_lead(
    db: Any, tenant_id: str, sequence_id: str, lead_id: str
) -> dict:
    """Manually enroll a lead in a sequence. Verifies ownership + lead tenancy."""
    # Verify sequence belongs to this tenant
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
            .eq("id", lead_id)
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
            "Failed to verify lead %s for tenant %s", lead_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to enroll lead")

    # Load active steps for the sequence
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
        db, sequence_id, steps, lead_id, tenant_id
    )
    if enrollment_id is None:
        raise HTTPException(
            status_code=500, detail="Failed to enroll lead (database error)"
        )

    return {
        "enrollment_id": enrollment_id,
        "sequence_id": sequence_id,
        "lead_id": lead_id,
        "steps_scheduled": len([s for s in steps if s.get("is_active", True)]),
    }
