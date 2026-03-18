"""Sales pipeline endpoints — stages, board view, analytics, and lead moves."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# ---------------------------------------------------------------------------
# Default stages seeded when a tenant has none
# ---------------------------------------------------------------------------

DEFAULT_STAGES = [
    {"name": "New Lead", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
    {"name": "Contacted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
    {"name": "Qualified", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
    {"name": "Proposal Sent", "sort_order": 3, "color": "#ec4899", "is_won": False, "is_lost": False},
    {"name": "Won", "sort_order": 4, "color": "#10b981", "is_won": True, "is_lost": False},
    {"name": "Lost", "sort_order": 5, "color": "#ef4444", "is_won": False, "is_lost": True},
]


def _seed_default_stages(tenant_id: str, db) -> list[dict]:
    """Insert default pipeline stages for a tenant and return them."""
    rows = [{"tenant_id": tenant_id, **s} for s in DEFAULT_STAGES]
    try:
        result = db.table("pipeline_stages").insert(rows).execute()
        return result.data or []
    except Exception:
        logger.exception("Failed to seed default pipeline stages for tenant %s", tenant_id)
        return []


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

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()

    # Fetch stage name so we can check leads by status value
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

    # Check whether any leads are in this stage (matched by status == stage name, case-insensitive)
    try:
        leads_check = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .ilike("status", stage_name)
            .execute()
        )
        lead_count = leads_check.count or 0
    except Exception:
        logger.exception("Failed to check leads in stage %s for tenant %s", stage_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to check stage occupancy")

    if lead_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete stage '{stage_name}' — {lead_count} lead(s) are in this stage. Move them first.",
        )

    # Safe to delete
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

    db = get_supabase()

    # Fetch stages
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

    # Fetch leads with deal columns. Uses client_id per schema rules.
    try:
        leads_result = (
            db.table("leads")
            .select(
                "id, name, email, deal_value, expected_close_date, "
                "lead_score, lead_temperature, status, stage_changed_at, created_at"
            )
            .eq("client_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load leads for pipeline board, tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load leads for pipeline board")

    leads = leads_result.data or []

    # Calculate days_in_stage for each lead
    now = datetime.now(timezone.utc)
    for lead in leads:
        changed_at = lead.get("stage_changed_at") or lead.get("created_at")
        if changed_at:
            try:
                if isinstance(changed_at, str):
                    dt = datetime.fromisoformat(changed_at.replace("Z", "+00:00"))
                else:
                    dt = changed_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                lead["days_in_stage"] = (now - dt).days
            except Exception:
                logger.warning("Failed to compute days_in_stage for lead %s", lead.get("id"))
                lead["days_in_stage"] = 0
        else:
            lead["days_in_stage"] = 0

    # Group leads by status (case-insensitive match against stage names)
    stage_names_lower = {s["name"].lower(): s["name"] for s in stages}
    leads_by_stage: dict[str, list] = {s["name"]: [] for s in stages}
    unmatched: list = []

    for lead in leads:
        status_lower = (lead.get("status") or "").lower()
        canonical_name = stage_names_lower.get(status_lower)
        if canonical_name:
            leads_by_stage[canonical_name].append(lead)
        else:
            unmatched.append(lead)

    # Leads with unrecognized statuses go into a catch-all bucket
    if unmatched:
        leads_by_stage["_unmatched"] = unmatched

    return {
        "stages": stages,
        "leads_by_stage": leads_by_stage,
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

    db = get_supabase()

    # Fetch stages so we know which are won/lost
    try:
        stages_result = (
            db.table("pipeline_stages")
            .select("name, is_won, is_lost")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.warning("Pipeline analytics: failed to load stages for tenant %s", tenant_id, exc_info=True)
        stages_result = type("R", (), {"data": []})()

    stages = stages_result.data or []
    won_stage_names = {s["name"].lower() for s in stages if s.get("is_won")}
    lost_stage_names = {s["name"].lower() for s in stages if s.get("is_lost")}

    # Fetch all leads with deal columns
    try:
        leads_result = (
            db.table("leads")
            .select("id, status, deal_value, stage_changed_at, created_at")
            .eq("client_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.warning("Pipeline analytics: failed to load leads for tenant %s", tenant_id, exc_info=True)
        leads_result = type("R", (), {"data": []})()

    leads = leads_result.data or []

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_pipeline_value = 0.0
    total_won_value = 0.0
    won_count = 0
    days_to_close_list: list[float] = []
    leads_by_stage: dict[str, int] = {}
    deals_this_month = 0
    won_this_month = 0
    total_closed = 0  # won + lost (used for conversion rate denominator)

    for lead in leads:
        status_lower = (lead.get("status") or "").lower()
        deal_value = float(lead.get("deal_value") or 0)
        is_won = status_lower in won_stage_names
        is_lost = status_lower in lost_stage_names

        # Pipeline value = all active deals (not lost)
        if not is_lost:
            total_pipeline_value += deal_value

        if is_won:
            total_won_value += deal_value
            won_count += 1
            total_closed += 1

            # Compute days-to-close using created_at as the start
            created_at = lead.get("created_at")
            changed_at = lead.get("stage_changed_at")
            if created_at and changed_at:
                try:
                    created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                    changed_dt = datetime.fromisoformat(str(changed_at).replace("Z", "+00:00"))
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    if changed_dt.tzinfo is None:
                        changed_dt = changed_dt.replace(tzinfo=timezone.utc)
                    days = (changed_dt - created_dt).days
                    if days >= 0:
                        days_to_close_list.append(float(days))
                except Exception:
                    logger.warning("Pipeline analytics: failed to parse dates for lead %s", lead.get("id"))

        if is_lost:
            total_closed += 1

        # Counts by stage name (use original status value for the key)
        original_status = lead.get("status") or "unknown"
        leads_by_stage[original_status] = leads_by_stage.get(original_status, 0) + 1

        # Deals this month (any lead created or stage-changed this month)
        changed_at = lead.get("stage_changed_at") or lead.get("created_at")
        if changed_at:
            try:
                dt = datetime.fromisoformat(str(changed_at).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= month_start:
                    deals_this_month += 1
                    if is_won:
                        won_this_month += 1
            except Exception:
                logger.warning("pipeline analytics: failed to parse dates for lead %s", lead.get("id"), exc_info=True)

    conversion_rate = round(won_count / total_closed * 100, 1) if total_closed > 0 else 0.0
    avg_deal_value = round(total_won_value / won_count, 2) if won_count > 0 else 0.0
    avg_days_to_close = round(sum(days_to_close_list) / len(days_to_close_list), 1) if days_to_close_list else 0.0

    return {
        "total_pipeline_value": round(total_pipeline_value, 2),
        "total_won_value": round(total_won_value, 2),
        "conversion_rate": conversion_rate,
        "avg_deal_value": avg_deal_value,
        "avg_days_to_close": avg_days_to_close,
        "leads_by_stage": leads_by_stage,
        "deals_this_month": deals_this_month,
        "won_this_month": won_this_month,
    }


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

    db = get_supabase()

    # Verify the lead belongs to this tenant
    try:
        lead_result = (
            db.table("leads")
            .select("id, status, name, email")
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
    new_status = req.status

    if old_status == new_status and req.deal_value is None:
        # No actual change — return the lead as-is
        return lead

    # Build update payload
    updates: dict = {
        "status": new_status,
        "stage_changed_at": datetime.now(timezone.utc).isoformat(),
    }
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
    except Exception:
        logger.exception("Failed to update lead %s stage for tenant %s", lead_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to move lead")

    if not update_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    updated_lead = update_result.data[0]

    # Log the stage change activity (fire-and-forget — never raises)
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
