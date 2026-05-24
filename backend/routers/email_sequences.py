"""Email Sequences endpoints — drip sequence builder with lead enrollment and send processing.

Heavy lifting lives in service modules:
- ``backend/services/email_sequence_schemas.py`` — Pydantic request models
- ``backend/services/email_sequence_sequence_ops.py`` — sequence CRUD
- ``backend/services/email_sequence_step_ops.py`` — step CRUD
- ``backend/services/email_sequence_enrollment.py`` — core enroll logic (also used by widget_lead)
- ``backend/services/email_sequence_enrollment_ops.py`` — HTTP-tier enrollment ops
- ``backend/services/email_sequence_processor.py`` — send processor

This router stays focused on HTTP wiring. The standalone callables
(``enroll_lead_in_sequences``, ``run_sequence_processor``) are re-exported so
existing imports from widget_lead, widget_lead_helpers, and main.py keep working.
``get_service_supabase`` stays imported at module scope so tests can patch it.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel  # noqa: F401  # kept for downstream imports

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.email_sequence_enrollment import (
    enroll_lead_in_sequence,  # noqa: F401  # re-exported for back-compat
    enroll_lead_in_sequences,
)
from backend.services.email_sequence_enrollment_ops import (
    list_enrollments_for_sequence,
    manual_enroll_lead,
)
from backend.services.email_sequence_processor import (
    process_due_sends,
    run_sequence_processor,
)
from backend.services.email_sequence_schemas import (
    EnrollRequest,
    SequenceCreate,
    SequenceUpdate,
    StepCreate,
    StepUpdate,
)
from backend.services.email_sequence_sequence_ops import (
    create_sequence_for_tenant,
    get_sequence_for_tenant,
    list_sequences_for_tenant,
    soft_delete_sequence,
    update_sequence_for_tenant,
)
from backend.services.email_sequence_step_ops import (
    add_step_to_sequence,
    delete_step_from_sequence,
    update_step_in_sequence,
)

__all__ = [
    "router",
    "enroll_lead_in_sequences",
    "enroll_lead_in_sequence",
    "run_sequence_processor",
    "get_service_supabase",
    "EnrollRequest",
    "SequenceCreate",
    "SequenceUpdate",
    "StepCreate",
    "StepUpdate",
]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/email-sequences", tags=["email-sequences"])


# ---------------------------------------------------------------------------
# CRUD — Sequences
# ---------------------------------------------------------------------------


@router.get("")
async def list_sequences(claims: dict = Depends(_get_current_tenant)):
    """List all email sequences for the tenant with step_count and enrollment_count."""
    return list_sequences_for_tenant(get_service_supabase(), claims["tenant_id"])


@router.post("", status_code=201)
async def create_sequence(
    req: SequenceCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new email sequence, optionally with steps in the same request."""
    return create_sequence_for_tenant(get_service_supabase(), claims["tenant_id"], req)


@router.get("/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single sequence with its steps and enrollment stats."""
    return get_sequence_for_tenant(
        get_service_supabase(), claims["tenant_id"], sequence_id
    )


@router.put("/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    req: SequenceUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update sequence fields and/or replace its step list."""
    return update_sequence_for_tenant(
        get_service_supabase(), claims["tenant_id"], sequence_id, req
    )


@router.delete("/{sequence_id}", status_code=204)
async def delete_sequence(
    sequence_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Soft-delete a sequence by setting is_active=False."""
    soft_delete_sequence(get_service_supabase(), claims["tenant_id"], sequence_id)


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
    return add_step_to_sequence(
        get_service_supabase(), claims["tenant_id"], sequence_id, req
    )


@router.put("/{sequence_id}/steps/{step_id}")
async def update_step(
    sequence_id: str,
    step_id: str,
    req: StepUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a step in a sequence."""
    return update_step_in_sequence(
        get_service_supabase(), claims["tenant_id"], sequence_id, step_id, req
    )


@router.delete("/{sequence_id}/steps/{step_id}", status_code=204)
async def delete_step(
    sequence_id: str,
    step_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a step from a sequence."""
    delete_step_from_sequence(
        get_service_supabase(), claims["tenant_id"], sequence_id, step_id
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
    return list_enrollments_for_sequence(
        get_service_supabase(), claims["tenant_id"], sequence_id
    )


@router.post("/{sequence_id}/enroll")
async def enroll_lead(
    sequence_id: str,
    req: EnrollRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Manually enroll a lead in a sequence."""
    return manual_enroll_lead(
        get_service_supabase(), claims["tenant_id"], sequence_id, req.lead_id
    )


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
