"""Admin Promotions CRUD — track and manage free/discounted business arrangements.

All endpoints are protected by the API secret key (internal admin only).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from starlette.requests import Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/promotions", tags=["admin-promotions"])

VALID_PROMOTION_TYPES = {
    "free_tier",
    "discount",
    "extended_trial",
    "partner_deal",
    "case_study",
    "referral",
}


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None = Header(None)) -> None:
    """Verify the caller has the platform admin secret."""
    import hmac as _hmac
    admin_secret = _admin_secret()
    if not admin_secret or not x_api_secret or not _hmac.compare_digest(x_api_secret, admin_secret):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _validate_iso_datetime(v: str | None) -> str | None:
    if v is None:
        return v
    try:
        datetime.fromisoformat(v)
    except (ValueError, TypeError):
        raise ValueError("expires_at must be a valid ISO 8601 datetime string")
    return v


class PromotionCreate(BaseModel):
    tenant_id: str
    promotion_type: str = Field(
        ..., description="free_tier, discount, extended_trial, partner_deal, case_study, referral"
    )
    discount_pct: int = Field(0, ge=0, le=100)
    reason: str | None = Field(None, max_length=1000)
    approved_by: str | None = Field(None, max_length=200)
    expires_at: str | None = None
    notes: str | None = Field(None, max_length=2000)

    @field_validator("expires_at")
    @classmethod
    def check_expires_at(cls, v):
        return _validate_iso_datetime(v)


class PromotionUpdate(BaseModel):
    discount_pct: int | None = Field(None, ge=0, le=100)
    reason: str | None = Field(None, max_length=1000)
    approved_by: str | None = Field(None, max_length=200)
    expires_at: str | None = None
    notes: str | None = Field(None, max_length=2000)

    @field_validator("expires_at")
    @classmethod
    def check_expires_at(cls, v):
        return _validate_iso_datetime(v)


@router.get("")
@limiter.limit("10/minute")
async def list_promotions(
    request: Request,
    x_api_secret: str | None = Header(None),
    promotion_type: str | None = Query(None),
    tenant_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all admin promotions with optional filters."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_supabase()

        query = (
            db.table("admin_promotions")
            .select(
                "*,tenants:tenant_id(id,business_name,owner_email,business_type,plan)"
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if promotion_type:
            query = query.eq("promotion_type", promotion_type)
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)

        result = query.execute()
        items = result.data or []

        # Total count
        count_query = db.table("admin_promotions").select("id", count="exact")
        if promotion_type:
            count_query = count_query.eq("promotion_type", promotion_type)
        if tenant_id:
            count_query = count_query.eq("tenant_id", tenant_id)
        total = (count_query.execute()).count or 0

        return {"promotions": items, "total": total}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list promotions")
        raise HTTPException(status_code=500, detail="Failed to list promotions")


@router.post("")
@limiter.limit("10/minute")
async def create_promotion(
    request: Request,
    req: PromotionCreate,
    x_api_secret: str | None = Header(None),
):
    """Create a new admin promotion for a tenant."""
    _verify_admin_secret(x_api_secret)

    if req.promotion_type not in VALID_PROMOTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid promotion_type. Must be one of: {', '.join(sorted(VALID_PROMOTION_TYPES))}",
        )

    try:
        db = get_supabase()

        # Verify tenant exists
        tenant_result = (
            db.table("tenants")
            .select("id, business_name, owner_email")
            .eq("id", req.tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant = tenant_result.data[0]

        # If this is a free_tier promotion, ensure the tenant is on free plan
        if req.promotion_type == "free_tier":
            tenant_full = (
                db.table("tenants")
                .select("plan")
                .eq("id", req.tenant_id)
                .limit(1)
                .execute()
            )
            if tenant_full.data and tenant_full.data[0].get("plan") != "free":
                raise HTTPException(
                    status_code=400,
                    detail="free_tier promotion can only be applied to tenants on the free plan",
                )

        # If discount > 0, update the tenant's admin_discount_pct
        if req.discount_pct > 0:
            db.table("tenants").update(
                {"admin_discount_pct": req.discount_pct}
            ).eq("id", req.tenant_id).execute()

        payload = {
            "tenant_id": req.tenant_id,
            "promotion_type": req.promotion_type,
            "discount_pct": req.discount_pct,
            "reason": req.reason,
            "approved_by": req.approved_by,
            "notes": req.notes,
            "expires_at": req.expires_at,
        }

        result = db.table("admin_promotions").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create promotion")

        logger.info(
            "Admin promotion created: tenant=%s (%s) type=%s discount=%d%% by=%s",
            req.tenant_id,
            tenant.get("business_name", "unknown"),
            req.promotion_type,
            req.discount_pct,
            req.approved_by or "unknown",
        )

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create promotion for tenant %s", req.tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create promotion")


@router.get("/{promotion_id}")
@limiter.limit("10/minute")
async def get_promotion(
    request: Request,
    promotion_id: str,
    x_api_secret: str | None = Header(None),
):
    """Get a single promotion with tenant details."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_supabase()

        result = (
            db.table("admin_promotions")
            .select("*,tenants:tenant_id(id,business_name,owner_email,business_type,plan)")
            .eq("id", promotion_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Promotion not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get promotion %s", promotion_id)
        raise HTTPException(status_code=500, detail="Failed to get promotion")


@router.put("/{promotion_id}")
@limiter.limit("10/minute")
async def update_promotion(
    request: Request,
    promotion_id: str,
    req: PromotionUpdate,
    x_api_secret: str | None = Header(None),
):
    """Update an existing promotion."""
    _verify_admin_secret(x_api_secret)

    updates = {}
    for k, v in req.model_dump().items():
        if v is not None:
            updates[k] = v

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        db = get_supabase()

        # Get current promotion to know tenant_id
        current = (
            db.table("admin_promotions")
            .select("tenant_id, discount_pct")
            .eq("id", promotion_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            raise HTTPException(status_code=404, detail="Promotion not found")

        # If discount_pct changed, update the tenant
        if "discount_pct" in updates and current.data[0].get("discount_pct") != updates.get("discount_pct"):
            db.table("tenants").update(
                {"admin_discount_pct": updates["discount_pct"]}
            ).eq("id", current.data[0]["tenant_id"]).execute()

        result = (
            db.table("admin_promotions")
            .update(updates)
            .eq("id", promotion_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Promotion not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update promotion %s", promotion_id)
        raise HTTPException(status_code=500, detail="Failed to update promotion")


@router.delete("/{promotion_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_promotion(
    request: Request,
    promotion_id: str,
    x_api_secret: str | None = Header(None),
):
    """Delete a promotion."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_supabase()

        result = (
            db.table("admin_promotions")
            .delete()
            .eq("id", promotion_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Promotion not found")

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete promotion %s", promotion_id)
        raise HTTPException(status_code=500, detail="Failed to delete promotion")


@router.post("/{promotion_id}/expire")
@limiter.limit("10/minute")
async def expire_promotion(
    request: Request,
    promotion_id: str,
    x_api_secret: str | None = Header(None),
):
    """Mark a promotion as expired by setting expires_at to now."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_supabase()

        now = datetime.now(timezone.utc).isoformat()
        result = (
            db.table("admin_promotions")
            .update({"expires_at": now})
            .eq("id", promotion_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Promotion not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to expire promotion %s", promotion_id)
        raise HTTPException(status_code=500, detail="Failed to expire promotion")
