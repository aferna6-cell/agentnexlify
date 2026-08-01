"""Lead prospecting endpoints: discover -> enrich -> score -> promote.

Tenant-scoped (client_id, same as leads — see backend/services/prospecting.py
docstring). Gated behind the `agent_os` plan (CLAUDE.md "Feature gating").

Not registered in backend/main.py — registration is a separate lane's task.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.prospecting import (
    ProspectingNotConfigured,
    discover,
    enrich_prospect,
    promote_to_lead,
    run_pipeline,
)
from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/prospecting",
    tags=["prospecting"],
    dependencies=[Depends(require_agent_os_access)],
)

_MAX_SEARCH_LIMIT = 25


class ProspectSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(20, ge=1, le=_MAX_SEARCH_LIMIT)
    auto_promote_threshold: float | None = Field(None, ge=0, le=100)


@router.get("/status")
async def prospecting_status(claims: dict = Depends(_get_current_tenant)):
    """Report whether the platform-level Places API key is configured."""
    return {"configured": bool(settings.google_places_api_key)}


@router.post("/search")
async def search_prospects(
    req: ProspectSearchRequest,
    tenant_id: str | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Run discover -> enrich -> score for one query/location. Bounded to
    <=25 results per call. Pass auto_promote_threshold to also promote
    qualifying rows straight to leads."""
    tenant_id = tenant_id or claims.get("tenant_id")
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        summary = await run_pipeline(
            db,
            client_id=tenant_id,
            query=req.query,
            location=req.location,
            limit=min(req.limit, _MAX_SEARCH_LIMIT),
            auto_promote_threshold=req.auto_promote_threshold,
        )
    except ProspectingNotConfigured:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "prospecting_not_configured",
                "message": "Prospecting isn't configured on this platform yet (missing Google Places API key).",
            },
        )
    except Exception:
        logger.exception("Prospect search failed tenant_id=%s", tenant_id)
        raise HTTPException(status_code=503, detail="Prospect search failed — please retry")

    return summary


@router.get("/prospects")
async def list_prospects(
    tenant_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    claims: dict = Depends(_get_current_tenant),
):
    """List prospects for a tenant, optionally filtered by status."""
    tenant_id = tenant_id or claims.get("tenant_id")
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        query = tenant_select(db, "prospects", tenant_id, "*", count="exact")
        if status:
            query = query.eq("status", status)
        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
        result = query.execute()
    except Exception:
        logger.exception("Prospect list query failed tenant_id=%s", tenant_id)
        raise HTTPException(status_code=503, detail="Prospect list query failed — please retry")

    total = result.count if result.count is not None else len(result.data or [])
    return {
        "prospects": result.data or [],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/prospects/{prospect_id}/enrich")
async def enrich_prospect_endpoint(
    prospect_id: str,
    tenant_id: str | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Re-run enrichment (website fetch + email/phone extraction) on demand."""
    tenant_id = tenant_id or claims.get("tenant_id")
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        updated = await enrich_prospect(db, client_id=tenant_id, prospect_id=prospect_id)
    except Exception:
        logger.exception(
            "Prospect enrichment failed tenant_id=%s prospect_id=%s", tenant_id, prospect_id
        )
        raise HTTPException(status_code=503, detail="Enrichment failed — please retry")

    if not updated:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return updated


@router.post("/prospects/{prospect_id}/promote")
async def promote_prospect(
    prospect_id: str,
    tenant_id: str | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Promote a prospect to a lead. Idempotent — re-promoting returns the
    existing lead rather than creating a duplicate."""
    tenant_id = tenant_id or claims.get("tenant_id")
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        lead = await promote_to_lead(db, client_id=tenant_id, prospect_id=prospect_id)
    except Exception:
        logger.exception(
            "Prospect promotion failed tenant_id=%s prospect_id=%s", tenant_id, prospect_id
        )
        raise HTTPException(status_code=503, detail="Promotion failed — please retry")

    if not lead:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return lead


@router.post("/prospects/{prospect_id}/reject")
async def reject_prospect(
    prospect_id: str,
    tenant_id: str | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Mark a prospect as rejected (excluded from future promotion)."""
    tenant_id = tenant_id or claims.get("tenant_id")
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            tenant_update(db, "prospects", tenant_id, {"status": "rejected"})
            .eq("id", prospect_id)
            .execute()
        )
    except Exception:
        logger.exception(
            "Prospect rejection failed tenant_id=%s prospect_id=%s", tenant_id, prospect_id
        )
        raise HTTPException(status_code=503, detail="Rejection failed — please retry")

    if not result.data:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return result.data[0]
