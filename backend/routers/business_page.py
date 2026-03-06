"""Business Page endpoints -- public hosted pages and dashboard management."""

import logging
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["business-page"])


# -- Schemas ------------------------------------------------------------------


class BusinessPagePublic(BaseModel):
    business_name: str
    description: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    hours_display: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    services: list[str] | None = None
    # Widget embedding
    widget_api_key: str | None = None
    widget_primary_color: str = "#00BFFF"
    widget_bot_name: str = "AI Assistant"
    widget_greeting: str | None = None
    widget_position: str = "bottom-right"


class BusinessPageUpdate(BaseModel):
    business_slug: str | None = None
    business_description: str | None = None
    business_phone: str | None = None
    business_address: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_hours_display: str | None = None
    business_logo_url: str | None = None
    business_cover_url: str | None = None
    business_page_enabled: bool | None = None
    business_services: list[str] | None = None


class BusinessPageSettings(BaseModel):
    business_slug: str | None = None
    business_description: str | None = None
    business_phone: str | None = None
    business_address: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_hours_display: str | None = None
    business_logo_url: str | None = None
    business_cover_url: str | None = None
    business_page_enabled: bool = False
    business_services: list[str] | None = None
    business_name: str | None = None


# -- Helpers ------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = _SLUG_RE.sub("-", text).strip("-")
    return text or "business"


def _ensure_unique_slug(db, slug: str, tenant_id: str | None = None) -> str:
    """Return a unique slug, appending -2, -3... if needed."""
    candidate = slug
    counter = 1
    while True:
        query = db.table("tenants").select("id").eq("business_slug", candidate).limit(1)
        if tenant_id:
            query = query.neq("id", tenant_id)
        result = query.execute()
        if not result.data:
            return candidate
        counter += 1
        candidate = f"{slug}-{counter}"


def _sanitize_slug(slug: str) -> str:
    """Sanitize user-provided slug."""
    slug = slug.lower().strip().strip("/")
    slug = _SLUG_RE.sub("-", slug).strip("-")
    if not slug or len(slug) < 2:
        raise HTTPException(status_code=400, detail="Slug must be at least 2 characters")
    if len(slug) > 80:
        raise HTTPException(status_code=400, detail="Slug must be 80 characters or less")
    return slug


# -- Public endpoint ----------------------------------------------------------


@router.get("/biz/{slug}", response_model=BusinessPagePublic)
@limiter.limit("120/minute")
async def get_business_page(request: Request, slug: str):
    """Public endpoint: return business page data for a given slug."""
    db = get_supabase()
    result = (
        db.table("tenants")
        .select(
            "id, business_name, business_description, business_phone, "
            "business_address, business_city, business_state, "
            "business_hours_display, business_logo_url, business_cover_url, "
            "business_page_enabled, business_services"
        )
        .eq("business_slug", slug)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Business page not found")

    tenant = result.data[0]
    if not tenant.get("business_page_enabled"):
        raise HTTPException(status_code=404, detail="Business page not found")

    # Get widget config for embedding
    widget_result = (
        db.table("widget_configs")
        .select("api_key, primary_color, bot_name, greeting_message, position")
        .eq("tenant_id", tenant["id"])
        .limit(1)
        .execute()
    )
    widget = widget_result.data[0] if widget_result.data else {}

    return BusinessPagePublic(
        business_name=tenant.get("business_name", ""),
        description=tenant.get("business_description"),
        phone=tenant.get("business_phone"),
        address=tenant.get("business_address"),
        city=tenant.get("business_city"),
        state=tenant.get("business_state"),
        hours_display=tenant.get("business_hours_display"),
        logo_url=tenant.get("business_logo_url"),
        cover_url=tenant.get("business_cover_url"),
        services=tenant.get("business_services"),
        widget_api_key=widget.get("api_key"),
        widget_primary_color=widget.get("primary_color", "#00BFFF"),
        widget_bot_name=widget.get("bot_name", "AI Assistant"),
        widget_greeting=widget.get("greeting_message"),
        widget_position=widget.get("position", "bottom-right"),
    )


# -- Dashboard endpoints ------------------------------------------------------


@router.get("/api/v1/business-page/{tenant_id}", response_model=BusinessPageSettings)
async def get_business_page_settings(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get business page settings for the dashboard."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    result = (
        db.table("tenants")
        .select(
            "business_name, business_slug, business_description, business_phone, "
            "business_address, business_city, business_state, "
            "business_hours_display, business_logo_url, business_cover_url, "
            "business_page_enabled, business_services"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    t = result.data[0]
    return BusinessPageSettings(
        business_name=t.get("business_name"),
        business_slug=t.get("business_slug"),
        business_description=t.get("business_description"),
        business_phone=t.get("business_phone"),
        business_address=t.get("business_address"),
        business_city=t.get("business_city"),
        business_state=t.get("business_state"),
        business_hours_display=t.get("business_hours_display"),
        business_logo_url=t.get("business_logo_url"),
        business_cover_url=t.get("business_cover_url"),
        business_page_enabled=t.get("business_page_enabled", False),
        business_services=t.get("business_services"),
    )


@router.put("/api/v1/business-page/{tenant_id}", response_model=BusinessPageSettings)
async def update_business_page(
    tenant_id: str,
    req: BusinessPageUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update business page settings."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    updates: dict = {}

    # Handle slug
    if req.business_slug is not None:
        slug = _sanitize_slug(req.business_slug)
        slug = _ensure_unique_slug(db, slug, tenant_id)
        updates["business_slug"] = slug

    # Handle other fields
    field_map = {
        "business_description": req.business_description,
        "business_phone": req.business_phone,
        "business_address": req.business_address,
        "business_city": req.business_city,
        "business_state": req.business_state,
        "business_hours_display": req.business_hours_display,
        "business_logo_url": req.business_logo_url,
        "business_cover_url": req.business_cover_url,
        "business_page_enabled": req.business_page_enabled,
        "business_services": req.business_services,
    }
    for key, value in field_map.items():
        if value is not None:
            updates[key] = value

    # When enabling, auto-generate slug if none exists
    if req.business_page_enabled and "business_slug" not in updates:
        existing = (
            db.table("tenants")
            .select("business_slug, business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if existing.data and not existing.data[0].get("business_slug"):
            name = existing.data[0].get("business_name", "business")
            slug = _slugify(name)
            slug = _ensure_unique_slug(db, slug, tenant_id)
            updates["business_slug"] = slug

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("tenants").update(updates).eq("id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    t = result.data[0]
    return BusinessPageSettings(
        business_name=t.get("business_name"),
        business_slug=t.get("business_slug"),
        business_description=t.get("business_description"),
        business_phone=t.get("business_phone"),
        business_address=t.get("business_address"),
        business_city=t.get("business_city"),
        business_state=t.get("business_state"),
        business_hours_display=t.get("business_hours_display"),
        business_logo_url=t.get("business_logo_url"),
        business_cover_url=t.get("business_cover_url"),
        business_page_enabled=t.get("business_page_enabled", False),
        business_services=t.get("business_services"),
    )
