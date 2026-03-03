"""Lead management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Header

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("/{tenant_id}")
async def get_leads(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Get all leads for a tenant, ordered by score descending."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    try:
        result = (
            db.table("leads")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("lead_score", desc=True)
            .execute()
        )
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
            .select("lead_stage, lead_score")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        leads = result.data or []
        return {
            "total": len(leads),
            "new": sum(1 for l in leads if l.get("lead_stage") == "new"),
            "contacted": sum(1 for l in leads if l.get("lead_stage") == "contacted"),
            "qualified": sum(1 for l in leads if l.get("lead_stage") == "qualified"),
            "converted": sum(1 for l in leads if l.get("lead_stage") == "converted"),
        }
    except Exception:
        logger.warning("Lead summary query failed for tenant %s", tenant_id, exc_info=True)
        return {"total": 0, "new": 0, "contacted": 0, "qualified": 0, "converted": 0}
