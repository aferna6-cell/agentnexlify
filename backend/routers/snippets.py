"""Snippets / Quick Replies — pre-written response templates for team conversations."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/snippets", tags=["snippets"])


class SnippetCreate(BaseModel):
    title: str = Field(..., max_length=100)
    content: str = Field(..., max_length=2000)
    shortcut: str | None = Field(None, max_length=30)
    category: str = Field("General", max_length=50)


class SnippetUpdate(BaseModel):
    title: str | None = Field(None, max_length=100)
    content: str | None = Field(None, max_length=2000)
    shortcut: str | None = Field(None, max_length=30)
    category: str | None = Field(None, max_length=50)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}")
async def list_snippets(
    tenant_id: str,
    category: str | None = None,
    search: str | None = Query(None, max_length=100),
    claims: dict = Depends(_get_current_tenant),
):
    """List snippets, sorted by usage_count descending (most-used first)."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("snippets")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("usage_count", desc=True)
    )

    if category:
        query = query.eq("category", category)
    if search:
        query = query.or_(f"title.ilike.%{search}%,content.ilike.%{search}%")

    result = query.execute()
    return {"snippets": result.data or []}


@router.get("/{tenant_id}/{snippet_id}")
async def get_snippet(
    tenant_id: str,
    snippet_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single snippet and increment its usage count."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("snippets")
        .select("*")
        .eq("id", snippet_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Snippet not found")

    snippet = result.data[0]

    # Increment usage count
    try:
        db.table("snippets").update({
            "usage_count": snippet["usage_count"] + 1
        }).eq("id", snippet_id).execute()
    except Exception:
        logger.warning("Failed to increment snippet usage count", exc_info=True)

    return snippet


@router.post("/{tenant_id}")
async def create_snippet(
    tenant_id: str,
    req: SnippetCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new snippet."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "title": req.title.strip(),
        "content": req.content.strip(),
        "category": req.category.strip(),
    }
    if req.shortcut:
        data["shortcut"] = req.shortcut.strip().lower()

    try:
        result = db.table("snippets").insert(data).execute()
    except Exception:
        raise HTTPException(status_code=409, detail="Shortcut already exists")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create snippet")
    return result.data[0]


@router.put("/{tenant_id}/{snippet_id}")
async def update_snippet(
    tenant_id: str,
    snippet_id: str,
    req: SnippetUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a snippet."""
    _verify_tenant(claims, tenant_id)

    updates = {}
    if req.title is not None:
        updates["title"] = req.title.strip()
    if req.content is not None:
        updates["content"] = req.content.strip()
    if req.shortcut is not None:
        updates["shortcut"] = req.shortcut.strip().lower() if req.shortcut else None
    if req.category is not None:
        updates["category"] = req.category.strip()

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("snippets")
        .update(updates)
        .eq("id", snippet_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return result.data[0]


@router.delete("/{tenant_id}/{snippet_id}")
async def delete_snippet(
    tenant_id: str,
    snippet_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a snippet."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    db.table("snippets").delete().eq("id", snippet_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}
