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
    # Tier features
    color_theme: str = "default"
    font_family: str | None = None
    hide_powered_by: bool = False
    custom_css: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None


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
    # Tier features
    bp_color_theme: str | None = None
    bp_font_family: str | None = None
    bp_hide_powered_by: bool | None = None
    bp_custom_css: str | None = None
    bp_meta_title: str | None = None
    bp_meta_description: str | None = None


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
    # Tier features
    bp_color_theme: str = "default"
    bp_font_family: str | None = None
    bp_hide_powered_by: bool = False
    bp_custom_css: str | None = None
    bp_meta_title: str | None = None
    bp_meta_description: str | None = None
    plan: str = "free"


# -- Helpers ------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Plan hierarchy for tier feature gating
_PLAN_RANK = {"free": 0, "growth": 1, "professional": 2, "enterprise": 3}

# Fields each plan unlocks (cumulative — higher plans include lower)
_TIER_FIELDS: dict[str, set[str]] = {
    "professional": {"bp_color_theme", "bp_font_family", "bp_hide_powered_by", "bp_meta_title", "bp_meta_description"},
    "enterprise": {"bp_custom_css"},
}

# All tier-gated column names (union of above)
_ALL_TIER_FIELDS = _TIER_FIELDS["professional"] | _TIER_FIELDS["enterprise"]

VALID_COLOR_THEMES = {
    "default", "ocean", "forest", "sunset", "slate",
    "rose", "amber", "indigo", "emerald", "charcoal",
}

VALID_FONTS = {
    "Inter", "Poppins", "Roboto", "Open Sans", "Lato",
    "Montserrat", "Raleway", "Nunito", "Source Sans 3", "DM Sans",
}


def _allowed_tier_fields(plan: str) -> set[str]:
    """Return the set of tier fields allowed for a given plan."""
    rank = _PLAN_RANK.get(plan, 0)
    allowed: set[str] = set()
    for tier, fields in _TIER_FIELDS.items():
        if rank >= _PLAN_RANK.get(tier, 999):
            allowed |= fields
    return allowed


def _strip_disallowed_tier_fields(updates: dict, plan: str) -> dict:
    """Remove tier-gated fields the tenant's plan doesn't allow."""
    allowed = _allowed_tier_fields(plan)
    return {k: v for k, v in updates.items() if k not in _ALL_TIER_FIELDS or k in allowed}


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
            "business_page_enabled, business_services, plan, "
            "bp_color_theme, bp_font_family, bp_hide_powered_by, "
            "bp_custom_css, bp_meta_title, bp_meta_description"
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

    # Only expose tier fields the plan actually allows
    plan = tenant.get("plan", "free")
    allowed = _allowed_tier_fields(plan)

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
        color_theme=tenant.get("bp_color_theme", "default") if "bp_color_theme" in allowed else "default",
        font_family=tenant.get("bp_font_family") if "bp_font_family" in allowed else None,
        hide_powered_by=tenant.get("bp_hide_powered_by", False) if "bp_hide_powered_by" in allowed else False,
        custom_css=tenant.get("bp_custom_css") if "bp_custom_css" in allowed else None,
        meta_title=tenant.get("bp_meta_title") if "bp_meta_title" in allowed else None,
        meta_description=tenant.get("bp_meta_description") if "bp_meta_description" in allowed else None,
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
            "business_page_enabled, business_services, plan, "
            "bp_color_theme, bp_font_family, bp_hide_powered_by, "
            "bp_custom_css, bp_meta_title, bp_meta_description"
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
        business_page_enabled=t.get("business_page_enabled") or False,
        business_services=t.get("business_services"),
        bp_color_theme=t.get("bp_color_theme") or "default",
        bp_font_family=t.get("bp_font_family"),
        bp_hide_powered_by=t.get("bp_hide_powered_by") or False,
        bp_custom_css=t.get("bp_custom_css"),
        bp_meta_title=t.get("bp_meta_title"),
        bp_meta_description=t.get("bp_meta_description"),
        plan=t.get("plan") or "free",
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

    # Fetch tenant plan for tier enforcement
    tenant_row = db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    plan = tenant_row.data[0].get("plan", "free") if tenant_row.data else "free"

    updates: dict = {}

    # Handle slug
    if req.business_slug is not None:
        slug = _sanitize_slug(req.business_slug)
        slug = _ensure_unique_slug(db, slug, tenant_id)
        updates["business_slug"] = slug

    # Handle content fields (all plans)
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

    # Handle tier fields — validate values then strip disallowed
    tier_fields = {
        "bp_color_theme": req.bp_color_theme,
        "bp_font_family": req.bp_font_family,
        "bp_hide_powered_by": req.bp_hide_powered_by,
        "bp_custom_css": req.bp_custom_css,
        "bp_meta_title": req.bp_meta_title,
        "bp_meta_description": req.bp_meta_description,
    }
    for key, value in tier_fields.items():
        if value is not None:
            updates[key] = value

    # Validate color theme
    if "bp_color_theme" in updates and updates["bp_color_theme"] not in VALID_COLOR_THEMES:
        raise HTTPException(status_code=400, detail=f"Invalid color theme. Must be one of: {', '.join(sorted(VALID_COLOR_THEMES))}")
    # Validate font
    if "bp_font_family" in updates and updates["bp_font_family"] not in VALID_FONTS:
        raise HTTPException(status_code=400, detail=f"Invalid font. Must be one of: {', '.join(sorted(VALID_FONTS))}")

    # Enforce plan restrictions — silently strip fields the plan doesn't allow
    updates = _strip_disallowed_tier_fields(updates, plan)

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
        business_page_enabled=t.get("business_page_enabled") or False,
        business_services=t.get("business_services"),
        bp_color_theme=t.get("bp_color_theme") or "default",
        bp_font_family=t.get("bp_font_family"),
        bp_hide_powered_by=t.get("bp_hide_powered_by") or False,
        bp_custom_css=t.get("bp_custom_css"),
        bp_meta_title=t.get("bp_meta_title"),
        bp_meta_description=t.get("bp_meta_description"),
        plan=plan or "free",
    )
