"""Sales pipeline endpoints — stages, board view, analytics, and lead moves."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.pipeline_analytics import (
    annotate_days_in_stage,
    compute_pipeline_metrics,
    group_leads_by_stage,
)
from backend.services.lead_status import (
    UnknownLeadStatus,
    canonical_lead_status,
    is_check_violation,
)
from backend.services.pipeline_presets import (
    DEFAULT_STAGES,
    _INDUSTRY_STAGES,
    _TYPE_ALIASES,
    seed_default_stages as _seed_default_stages,
)
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# Re-exports so existing test imports keep working (Rule 10: never change tests).
__all__ = ["router", "DEFAULT_STAGES", "_INDUSTRY_STAGES", "_TYPE_ALIASES"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class StageCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#3b82f6", max_length=20)
    sort_order: int = Field(default=0, ge=0)
    is_won: bool = False
    is_lost: bool = False


class StageUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = Field(default=None, ge=0)
    is_won: bool | None = None
    is_lost: bool | None = None


class MoveleadRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=100)
    pipeline_stage: str | None = Field(default=None, max_length=100)
    deal_value: float | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Stage management
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/stages")
async def list_stages(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List pipeline stages ordered by sort_order. Auto-seeds defaults if none exist."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("pipeline_stages")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("sort_order", desc=False)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list pipeline stages for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load pipeline stages")

    stages = result.data or []

    if not stages:
        stages = _seed_default_stages(tenant_id, db)

    return {"stages": stages}


@router.post("/{tenant_id}/stages", status_code=201)
async def create_stage(
    tenant_id: str,
    req: StageCreateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a custom pipeline stage."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("pipeline_stages")
            .insert({
                "tenant_id": tenant_id,
                "name": req.name,
                "color": req.color,
                "sort_order": req.sort_order,
                "is_won": req.is_won,
                "is_lost": req.is_lost,
            })
            .execute()
        )
    except Exception:
        logger.exception("Failed to create pipeline stage for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create stage")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create stage")

    return result.data[0]


@router.put("/{tenant_id}/stages/{stage_id}")
async def update_stage(
    tenant_id: str,
    stage_id: str,
    req: StageUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a pipeline stage (name, color, sort_order)."""
    verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    try:
        result = (
            db.table("pipeline_stages")
            .update(updates)
            .eq("id", stage_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update pipeline stage %s for tenant %s", stage_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update stage")

    if not result.data:
        raise HTTPException(status_code=404, detail="Stage not found")

    return result.data[0]


@router.delete("/{tenant_id}/stages/{stage_id}", status_code=204)
async def delete_stage(
    tenant_id: str,
    stage_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a pipeline stage. Fails if any leads are currently in this stage."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    try:
        stage_result = (
            db.table("pipeline_stages")
            .select("id, name")
            .eq("id", stage_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch stage %s for tenant %s", stage_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch stage")

    if not stage_result.data:
        raise HTTPException(status_code=404, detail="Stage not found")

    stage_name = stage_result.data[0]["name"]

    try:
        by_label = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .eq("pipeline_stage", stage_name)
            .execute()
        )
        by_status = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .ilike("status", stage_name)
            .execute()
        )
        lead_count = (by_label.count or 0) + (by_status.count or 0)
    except Exception:
        logger.exception("Failed to check leads in stage %s for tenant %s", stage_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to check stage occupancy")

    if lead_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete stage '{stage_name}' — {lead_count} lead(s) are in this stage. Move them first.",
        )

    try:
        db.table("pipeline_stages").delete().eq("id", stage_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to delete pipeline stage %s for tenant %s", stage_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete stage")

    from fastapi.responses import Response
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Pipeline board
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/board")
async def get_pipeline_board(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get all leads grouped by status with deal values and time-in-stage metrics."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    try:
        stages_result = (
            db.table("pipeline_stages")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("sort_order", desc=False)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load pipeline stages for board, tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load pipeline board")

    stages = stages_result.data or []
    if not stages:
        stages = _seed_default_stages(tenant_id, db)

    try:
        leads_result = (
            db.table("leads")
            .select(
                "id, name, email, deal_value, expected_close_date, "
                "lead_score, lead_temperature, status, pipeline_stage, "
                "stage_changed_at, created_at"
            )
            .eq("client_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load leads for pipeline board, tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load leads for pipeline board")

    leads = leads_result.data or []
    annotate_days_in_stage(leads)

    return {
        "stages": stages,
        "leads_by_stage": group_leads_by_stage(leads, stages),
    }


# ---------------------------------------------------------------------------
# Pipeline analytics
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/analytics")
async def get_pipeline_analytics(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Pipeline metrics: pipeline value, won value, conversion rate, avg deal, avg days-to-close."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    try:
        stages_result = (
            db.table("pipeline_stages")
            .select("name, is_won, is_lost")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        stages = stages_result.data or []
    except Exception:
        logger.warning("Pipeline analytics: failed to load stages for tenant %s", tenant_id, exc_info=True)
        stages = []

    try:
        leads_result = (
            db.table("leads")
            .select("id, status, deal_value, stage_changed_at, created_at")
            .eq("client_id", tenant_id)
            .execute()
        )
        leads = leads_result.data or []
    except Exception:
        logger.warning("Pipeline analytics: failed to load leads for tenant %s", tenant_id, exc_info=True)
        leads = []

    return compute_pipeline_metrics(leads, stages)


# ---------------------------------------------------------------------------
# Lead stage transition
# ---------------------------------------------------------------------------

@router.put("/{tenant_id}/move/{lead_id}")
async def move_lead(
    tenant_id: str,
    lead_id: str,
    req: MoveleadRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Move a lead to a new pipeline stage. Updates status and stage_changed_at."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    try:
        lead_result = (
            db.table("leads")
            .select("id, status, pipeline_stage, name, email")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch lead %s for tenant %s", lead_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch lead")

    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = lead_result.data[0]
    old_status = lead.get("status", "")
    stage_label = (req.pipeline_stage or "").strip() or None
    try:
        new_status = canonical_lead_status(req.status)
    except UnknownLeadStatus as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown lead status '{exc.raw}'. "
                "Allowed: new, contacted, appointment_booked, closed, lost."
            ),
        )
    if stage_label is None and req.status.strip() != new_status:
        stage_label = req.status.strip()

    if (
        old_status == new_status
        and (lead.get("pipeline_stage") or None) == stage_label
        and req.deal_value is None
    ):
        return lead

    updates: dict = {
        "status": new_status,
        "stage_changed_at": datetime.now(timezone.utc).isoformat(),
    }
    if stage_label is not None:
        updates["pipeline_stage"] = stage_label
    if req.deal_value is not None:
        updates["deal_value"] = req.deal_value

    try:
        update_result = (
            db.table("leads")
            .update(updates)
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .execute()
        )
    except Exception as exc:
        if is_check_violation(exc):
            raise HTTPException(
                status_code=422,
                detail="Lead data violates a database check constraint",
            ) from exc
        logger.exception("Failed to update lead %s stage for tenant %s", lead_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to move lead")

    if not update_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    updated_lead = update_result.data[0]

    lead_display = lead.get("name") or lead.get("email") or lead_id
    log_activity(
        tenant_id=tenant_id,
        activity_type="status_change",
        description=f"Moved {lead_display} to {new_status}",
        lead_id=lead_id,
        metadata={"old_status": old_status, "new_status": new_status},
    )

    fire_event_background(tenant_id, "lead.status_changed", {
        "lead_id": lead_id,
        "old_status": old_status,
        "new_status": new_status,
        "lead_name": lead.get("name"),
        "source": "pipeline_move",
    })

    return updated_lead
