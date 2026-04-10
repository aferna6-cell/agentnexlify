"""Lead scoring configuration — per-tenant customizable scoring weights."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])

# Default scoring factors seeded for new tenants
DEFAULT_FACTORS = [
    {"factor": "contact_info", "weight": 25, "description": "Has email and/or phone number"},
    {"factor": "engagement", "weight": 20, "description": "Number of messages exchanged"},
    {"factor": "intent_signals", "weight": 20, "description": "Mentions pricing, timeline, or booking"},
    {"factor": "urgency", "weight": 15, "description": "Uses urgent language (ASAP, emergency, today)"},
    {"factor": "budget_signals", "weight": 10, "description": "Mentions budget, payment, or price range"},
    {"factor": "recency", "weight": 10, "description": "How recently the lead was active"},
]


class ScoringFactorUpdate(BaseModel):
    weight: int = Field(..., ge=0, le=100)
    is_enabled: bool = True


class ScoringFactorCreate(BaseModel):
    factor: str = Field(..., min_length=1, max_length=100)
    weight: int = Field(10, ge=0, le=100)
    description: str | None = None
    is_enabled: bool = True


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _seed_defaults(db, tenant_id: str):
    """Seed default scoring factors for a tenant if none exist."""
    existing = db.table("scoring_configs").select("id").eq("tenant_id", tenant_id).limit(1).execute()
    if existing.data:
        return  # Already seeded

    rows = []
    for f in DEFAULT_FACTORS:
        rows.append({
            "tenant_id": tenant_id,
            "factor": f["factor"],
            "weight": f["weight"],
            "description": f["description"],
            "is_enabled": True,
        })
    try:
        db.table("scoring_configs").insert(rows).execute()
        logger.info("Seeded %d default scoring factors for tenant %s", len(rows), tenant_id)
    except Exception:
        logger.exception("Failed to seed scoring configs for tenant %s", tenant_id)


@router.get("/{tenant_id}")
async def list_scoring_factors(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all scoring factors for a tenant. Seeds defaults on first access."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    _seed_defaults(db, tenant_id)

    result = (
        db.table("scoring_configs")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("weight", desc=True)
        .execute()
    )
    return {"factors": result.data or []}


@router.put("/{tenant_id}/{factor_id}")
async def update_scoring_factor(
    tenant_id: str,
    factor_id: str,
    req: ScoringFactorUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update the weight or enabled state of a scoring factor."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    result = (
        db.table("scoring_configs")
        .update({"weight": req.weight, "is_enabled": req.is_enabled})
        .eq("id", factor_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scoring factor not found")
    return result.data[0]


@router.post("/{tenant_id}")
async def create_scoring_factor(
    tenant_id: str,
    req: ScoringFactorCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a custom scoring factor."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    data = {
        "tenant_id": tenant_id,
        "factor": req.factor.strip().lower().replace(" ", "_"),
        "weight": req.weight,
        "description": req.description,
        "is_enabled": req.is_enabled,
    }
    try:
        result = db.table("scoring_configs").insert(data).execute()
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="A factor with this name already exists")
        raise

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create scoring factor")
    return result.data[0]


@router.delete("/{tenant_id}/{factor_id}")
async def delete_scoring_factor(
    tenant_id: str,
    factor_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a custom scoring factor."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    db.table("scoring_configs").delete().eq("id", factor_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}


@router.post("/{tenant_id}/reset")
async def reset_to_defaults(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Reset scoring factors to defaults (deletes all custom factors)."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    # Delete all existing
    db.table("scoring_configs").delete().eq("tenant_id", tenant_id).execute()

    # Re-seed defaults
    rows = []
    for f in DEFAULT_FACTORS:
        rows.append({
            "tenant_id": tenant_id,
            "factor": f["factor"],
            "weight": f["weight"],
            "description": f["description"],
            "is_enabled": True,
        })
    db.table("scoring_configs").insert(rows).execute()
    return {"message": "Reset to defaults", "factors_count": len(rows)}
