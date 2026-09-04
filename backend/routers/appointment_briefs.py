"""Appointment intelligence — pre-meeting briefs + follow-up drafts.

Separate module from appointments.py (already ~700 lines) per Rule 12.
Both endpoints return drafts for owner approval; nothing here sends.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import _get_current_tenant, block_demo_role
from backend.models.database import get_service_supabase
from backend.services import appointment_brief
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.ai_usage_guard import get_ai_usage_status

logger = logging.getLogger(__name__)

# GH #643 / PR #575 salvage: both endpoints drive Claude calls, so they carry
# the full guard stack — demo block + agent_os plan gate at the router, usage
# cap per call. DemoRoleBlockMiddleware already 403s demo POSTs here; the
# Depends pins the invariant. chatbot/free still need the 402 plan gate.
router = APIRouter(
    prefix="/api/v1/appointments",
    tags=["appointment-briefs"],
    dependencies=[Depends(block_demo_role), Depends(require_agent_os_access)],
)


def _check_ai_budget(db, tenant_id: str) -> None:
    """429 when the tenant's monthly AI hard limit is spent; fail-open on errors."""
    try:
        status = get_ai_usage_status(db, tenant_id)
    except Exception:
        logger.warning(
            "ai usage check failed tenant=%s - failing open", tenant_id, exc_info=True
        )
        return
    if status.get("hard_limit_reached"):
        raise HTTPException(
            status_code=429,
            detail="Monthly AI usage limit reached — add a usage pack or wait for the next cycle",
        )


def _business_name(db, tenant_id: str) -> str:
    try:
        rows = (
            db.table("tenants")
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
        return (rows[0].get("business_name") or "") if rows else ""
    except Exception:
        logger.warning("business_name lookup failed for %s", tenant_id, exc_info=True)
        return ""


@router.post("/{tenant_id}/{appointment_id}/brief")
async def get_appointment_brief(
    tenant_id: str,
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """One-page pre-meeting brief: who they are, what they want, talking points."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_service_supabase()
    _check_ai_budget(db, tenant_id)
    try:
        return await appointment_brief.generate_brief(
            db, tenant_id, appointment_id, _business_name(db, tenant_id)
        )
    except appointment_brief.AppointmentBriefError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception(
            "Appointment brief failed tenant=%s appt=%s", tenant_id, appointment_id
        )
        raise HTTPException(status_code=502, detail="Brief generation failed")


@router.post("/{tenant_id}/{appointment_id}/follow-up-draft")
async def get_followup_draft(
    tenant_id: str,
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Draft a follow-up email for the owner to review — never auto-sent."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_service_supabase()
    _check_ai_budget(db, tenant_id)
    try:
        return await appointment_brief.draft_followup(
            db, tenant_id, appointment_id, _business_name(db, tenant_id)
        )
    except appointment_brief.AppointmentBriefError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception(
            "Follow-up draft failed tenant=%s appt=%s", tenant_id, appointment_id
        )
        raise HTTPException(status_code=502, detail="Follow-up draft failed")
