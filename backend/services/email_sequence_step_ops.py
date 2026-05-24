"""Step-level DB operations for the email-sequence router.

CRUD helpers for the ``email_sequence_steps`` table. Mirrors the structure of
``email_sequence_sequence_ops.py`` — pure functions that take ``db`` + ids and
raise ``HTTPException`` on failure.
"""

import logging
from typing import Any

from fastapi import HTTPException

from backend.services.email_sequence_schemas import StepCreate, StepUpdate

logger = logging.getLogger(__name__)

__all__ = [
    "verify_sequence_ownership",
    "add_step_to_sequence",
    "update_step_in_sequence",
    "delete_step_from_sequence",
]


def verify_sequence_ownership(
    db: Any,
    tenant_id: str,
    sequence_id: str,
    failure_detail: str,
) -> None:
    """Raise 404 if sequence_id doesn't belong to tenant_id, 500 on DB error."""
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
        raise HTTPException(status_code=500, detail=failure_detail)


def add_step_to_sequence(
    db: Any,
    tenant_id: str,
    sequence_id: str,
    req: StepCreate,
) -> dict:
    """Insert a new step into a sequence. Verifies ownership first."""
    verify_sequence_ownership(db, tenant_id, sequence_id, "Failed to add step")

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


def update_step_in_sequence(
    db: Any,
    tenant_id: str,
    sequence_id: str,
    step_id: str,
    req: StepUpdate,
) -> dict:
    """Update an existing step. Verifies sequence ownership first."""
    verify_sequence_ownership(db, tenant_id, sequence_id, "Failed to update step")

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


def delete_step_from_sequence(
    db: Any,
    tenant_id: str,
    sequence_id: str,
    step_id: str,
) -> None:
    """Delete a step. Verifies sequence ownership first."""
    verify_sequence_ownership(db, tenant_id, sequence_id, "Failed to delete step")

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
