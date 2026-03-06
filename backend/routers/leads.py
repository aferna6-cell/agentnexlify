"""Lead management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import Response

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import LeadScoreResponse, LeadUpdateRequest, ScoreAllResponse
from backend.routers.auth import _get_current_tenant
from backend.services.lead_scoring import score_all_leads, score_lead
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("/{tenant_id}")
async def get_leads(
    tenant_id: str,
    stage: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("lead_score"),
    order: str = Query("desc"),
    claims: dict = Depends(_get_current_tenant),
):
    """Get all leads for a tenant, with optional filtering/sorting."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    try:
        query = db.table("leads").select("*").eq("client_id", tenant_id)

        if stage:
            query = query.eq("status", stage)

        if search:
            query = query.or_(
                f"name.ilike.%{search}%,email.ilike.%{search}%,phone.ilike.%{search}%"
            )

        desc = order.lower() == "desc"
        query = query.order(sort, desc=desc)

        result = query.execute()
        return {"leads": result.data or []}
    except Exception:
        logger.warning("Leads query failed for tenant %s", tenant_id, exc_info=True)
        return {"leads": []}


@router.get("/{tenant_id}/summary")
async def get_lead_summary(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Get a summary of lead counts by stage."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    try:
        result = (
            db.table("leads")
            .select("status, lead_score")
            .eq("client_id", tenant_id)
            .execute()
        )
        leads = result.data or []
        return {
            "total": len(leads),
            "new": sum(1 for l in leads if l.get("status") == "new"),
            "contacted": sum(1 for l in leads if l.get("status") == "contacted"),
            "appointment_booked": sum(1 for l in leads if l.get("status") == "appointment_booked"),
            "closed": sum(1 for l in leads if l.get("status") == "closed"),
            "lost": sum(1 for l in leads if l.get("status") == "lost"),
        }
    except Exception:
        logger.warning("Lead summary query failed for tenant %s", tenant_id, exc_info=True)
        return {"total": 0, "new": 0, "contacted": 0, "appointment_booked": 0, "closed": 0, "lost": 0}


@router.post("/{tenant_id}/score-all", response_model=ScoreAllResponse)
async def rescore_all(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Re-score all leads for a tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = score_all_leads(tenant_id)
    return ScoreAllResponse(**result)


@router.get("/{tenant_id}/{lead_id}/score", response_model=LeadScoreResponse)
async def get_lead_score(
    tenant_id: str, lead_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Get detailed score breakdown for a single lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        result = score_lead(lead_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadScoreResponse(**result)


@router.patch("/{tenant_id}/{lead_id}")
async def update_lead(
    tenant_id: str,
    lead_id: str,
    req: LeadUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a lead's fields."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("leads")
        .update(updates)
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    fire_event_background(tenant_id, "lead.updated", {
        "lead_id": lead_id,
        "updated_fields": list(updates.keys()),
        **updates,
    })

    return result.data[0]


@router.delete("/{tenant_id}/{lead_id}", status_code=204)
async def delete_lead(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("leads")
        .delete()
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Response(status_code=204)
