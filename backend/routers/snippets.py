"""Snippets / Quick Replies — pre-written response templates for team conversations."""

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.services.llm_runtime import call_claude_messages
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
        import re
        safe_search = re.sub(r"[^a-zA-Z0-9@_ \-+.]", "", search).strip()[:100]
        if safe_search:
            query = query.or_(f"title.ilike.%{safe_search}%,content.ilike.%{safe_search}%")

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


class SuggestRequest(BaseModel):
    conversation_context: str = Field(..., max_length=3000)


@router.post("/{tenant_id}/suggest")
async def suggest_snippet(
    tenant_id: str,
    req: SuggestRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI suggests the best matching snippet based on conversation context."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    snippets_result = (
        db.table("snippets")
        .select("id, title, content, category")
        .eq("tenant_id", tenant_id)
        .order("usage_count", desc=True)
        .limit(20)
        .execute()
    )
    snippets = snippets_result.data or []
    if not snippets:
        return {"suggestion": None, "reason": "No snippets available"}

    snippet_list = "\n".join(
        f"[{i}] {s['title']} ({s['category']}): {s['content'][:100]}"
        for i, s in enumerate(snippets)
    )

    try:
        resp = await call_claude_messages(
            operation="snippets.suggest",
            model="claude-sonnet-4-6",
            max_tokens=50,
            temperature=0,
            timeout=30.0,
            system=(
                "You are a snippet suggestion engine. Given a conversation context and a list of available snippets, "
                "return ONLY the number [N] of the best matching snippet, or 'none' if no snippet is relevant.\n"
                "Output ONLY the number or 'none'. No explanation."
            ),
            messages=[{"role": "user", "content": f"Conversation:\n{req.conversation_context}\n\nAvailable snippets:\n{snippet_list}"}],
            metadata={"tenant_id": tenant_id, "snippet_count": len(snippets)},
        )
        answer = resp.text.strip().lower()
        if answer == "none":
            return {"suggestion": None, "reason": "No relevant snippet found"}

        # Parse the index
        idx_str = answer.strip("[]")
        try:
            idx = int(idx_str)
        except ValueError:
            return {"suggestion": None, "reason": "AI returned invalid response"}

        if 0 <= idx < len(snippets):
            return {"suggestion": snippets[idx]}
        return {"suggestion": None, "reason": "AI returned out-of-range index"}
    except anthropic.APIError as e:
        logger.warning("Snippet suggestion API error: %s", e)
        return {"suggestion": None, "reason": "AI service unavailable"}
