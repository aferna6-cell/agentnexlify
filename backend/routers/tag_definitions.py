"""Tag definitions CRUD — manage AI conversation auto-categorization tags."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])

SYSTEM_TAGS = [
    {"tag_name": "New Lead", "tag_color": "#3b82f6"},
    {"tag_name": "Pricing Question", "tag_color": "#f59e0b"},
    {"tag_name": "Complaint", "tag_color": "#ef4444"},
    {"tag_name": "Appointment Request", "tag_color": "#22c55e"},
    {"tag_name": "Urgent", "tag_color": "#dc2626"},
    {"tag_name": "Follow-up Needed", "tag_color": "#8b5cf6"},
]


class TagCreate(BaseModel):
    tag_name: str = Field(..., max_length=50)
    tag_color: str = Field("#6b7280", max_length=10)


class TagUpdate(BaseModel):
    tag_name: str | None = Field(None, max_length=50)
    tag_color: str | None = Field(None, max_length=10)
    is_enabled: bool | None = None


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _ensure_system_tags(db, tenant_id: str) -> None:
    """Seed system tags for a tenant if they don't exist yet."""
    for tag in SYSTEM_TAGS:
        try:
            db.table("tenant_tag_definitions").insert({
                "tenant_id": tenant_id,
                "tag_name": tag["tag_name"],
                "tag_color": tag["tag_color"],
                "is_system": True,
            }).execute()
        except Exception:
            logger.debug("Tag '%s' already exists for tenant %s (unique constraint)", tag["tag_name"], tenant_id)


@router.get("/{tenant_id}")
async def list_tag_definitions(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all tag definitions for a tenant. Seeds system tags on first access."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Check if tags exist; if not, seed system tags
    result = (
        db.table("tenant_tag_definitions")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("is_system", desc=True)
        .order("tag_name")
        .execute()
    )
    if not result.data:
        _ensure_system_tags(db, tenant_id)
        result = (
            db.table("tenant_tag_definitions")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("is_system", desc=True)
            .order("tag_name")
            .execute()
        )

    return {"tags": result.data or []}


@router.post("/{tenant_id}")
async def create_tag_definition(
    tenant_id: str,
    req: TagCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a custom tag definition."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    data = {
        "tenant_id": tenant_id,
        "tag_name": req.tag_name.strip(),
        "tag_color": req.tag_color,
        "is_system": False,
    }
    try:
        result = db.table("tenant_tag_definitions").insert(data).execute()
    except Exception:
        raise HTTPException(status_code=409, detail="Tag name already exists")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create tag")
    return result.data[0]


@router.put("/{tenant_id}/{tag_id}")
async def update_tag_definition(
    tenant_id: str,
    tag_id: str,
    req: TagUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a tag definition. System tags can only toggle is_enabled."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Check if system tag
    existing = (
        db.table("tenant_tag_definitions")
        .select("is_system")
        .eq("id", tag_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Tag not found")

    is_system = existing.data[0].get("is_system", False)
    updates = {}

    if is_system:
        # System tags: only allow toggling is_enabled
        if req.is_enabled is not None:
            updates["is_enabled"] = req.is_enabled
    else:
        if req.tag_name is not None:
            updates["tag_name"] = req.tag_name.strip()
        if req.tag_color is not None:
            updates["tag_color"] = req.tag_color
        if req.is_enabled is not None:
            updates["is_enabled"] = req.is_enabled

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        db.table("tenant_tag_definitions")
        .update(updates)
        .eq("id", tag_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tag not found")
    return result.data[0]


@router.delete("/{tenant_id}/{tag_id}")
async def delete_tag_definition(
    tenant_id: str,
    tag_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a custom tag definition. System tags cannot be deleted."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Check if system tag
    existing = (
        db.table("tenant_tag_definitions")
        .select("is_system")
        .eq("id", tag_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if existing.data and existing.data[0].get("is_system"):
        raise HTTPException(status_code=400, detail="System tags cannot be deleted — disable them instead")

    db.table("tenant_tag_definitions").delete().eq("id", tag_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}
