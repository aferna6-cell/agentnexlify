"""Content Studio endpoints — source content CRUD and AI repurposing."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/content", tags=["content"])


# --- Models ---

class ContentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    source_type: str = "text"  # text, description, file
    source_content: str = Field(..., min_length=1, max_length=50000)
    tags: list[str] | None = None


class ContentUpdate(BaseModel):
    title: str | None = None
    source_content: str | None = None
    platform_versions: dict | None = None
    status: str | None = None
    tags: list[str] | None = None


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Endpoints ---

@router.get("/{tenant_id}")
async def list_content(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List content items with optional status filter."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("content_items")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    items = result.data or []

    # Get total count for pagination
    count_query = (
        db.table("content_items")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
    )
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()
    total = count_result.count if count_result.count is not None else len(items)

    return {"items": items, "total": total}


@router.get("/{tenant_id}/{content_id}")
async def get_content(
    tenant_id: str,
    content_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single content item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("content_items")
        .select("*")
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")

    return result.data[0]


@router.post("/{tenant_id}")
async def create_content(
    tenant_id: str,
    req: ContentCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new content item (source content for repurposing)."""
    _verify_tenant(claims, tenant_id)

    payload = {
        "tenant_id": tenant_id,
        "title": req.title,
        "source_type": req.source_type,
        "source_content": req.source_content,
        "status": "draft",
    }
    if req.tags:
        payload["tags"] = req.tags[:10]  # max 10 tags

    db = get_supabase()
    result = db.table("content_items").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create content")

    return result.data[0]


@router.patch("/{tenant_id}/{content_id}")
async def update_content(
    tenant_id: str,
    content_id: str,
    req: ContentUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a content item."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "tags" in updates:
        updates["tags"] = updates["tags"][:10]

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_supabase()
    result = (
        db.table("content_items")
        .update(updates)
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")

    return result.data[0]


@router.delete("/{tenant_id}/{content_id}", status_code=204)
async def delete_content(
    tenant_id: str,
    content_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a content item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("content_items")
        .delete()
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")
