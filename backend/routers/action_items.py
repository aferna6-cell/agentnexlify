"""Action items CRUD — AI-extracted tasks from conversations."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/action-items", tags=["action-items"])


class ActionItemCreate(BaseModel):
    description: str = Field(..., max_length=500)
    conversation_id: str | None = None
    lead_id: str | None = None
    due_date: date | None = None
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    assigned_to: str | None = None


class ActionItemUpdate(BaseModel):
    description: str | None = Field(None, max_length=500)
    due_date: date | None = None
    priority: str | None = Field(None, pattern="^(low|medium|high)$")
    status: str | None = Field(None, pattern="^(pending|done|dismissed)$")
    assigned_to: str | None = None


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}")
async def list_action_items(
    tenant_id: str,
    status: str = Query(None, pattern="^(pending|done|dismissed)$"),
    priority: str = Query(None, pattern="^(low|medium|high)$"),
    limit: int = Query(50, ge=1, le=200),
    claims: dict = Depends(_get_current_tenant),
):
    """List action items for a tenant, optionally filtered by status/priority."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    query = (
        db.table("action_items")
        .select("*, leads(name, email), team_members(name)")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)
    if priority:
        query = query.eq("priority", priority)

    result = query.execute()
    return {"items": result.data or [], "count": len(result.data or [])}


@router.get("/{tenant_id}/summary")
async def action_items_summary(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get counts by status for the dashboard widget."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("action_items")
        .select("status")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    items = result.data or []
    pending = sum(1 for i in items if i["status"] == "pending")
    overdue = 0
    today = date.today().isoformat()

    # Query pending with due_date
    overdue_result = (
        db.table("action_items")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "pending")
        .lt("due_date", today)
        .execute()
    )
    overdue = overdue_result.count or 0

    return {
        "pending": pending,
        "overdue": overdue,
        "done": sum(1 for i in items if i["status"] == "done"),
        "dismissed": sum(1 for i in items if i["status"] == "dismissed"),
    }


@router.post("/{tenant_id}")
async def create_action_item(
    tenant_id: str,
    req: ActionItemCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create an action item manually."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    data = {
        "tenant_id": tenant_id,
        "description": req.description.strip(),
        "priority": req.priority,
    }
    if req.conversation_id:
        data["conversation_id"] = req.conversation_id
    if req.lead_id:
        data["lead_id"] = req.lead_id
    if req.due_date:
        data["due_date"] = req.due_date.isoformat()
    if req.assigned_to:
        data["assigned_to"] = req.assigned_to

    result = db.table("action_items").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create action item")
    return result.data[0]


@router.put("/{tenant_id}/{item_id}")
async def update_action_item(
    tenant_id: str,
    item_id: str,
    req: ActionItemUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update an action item (status, priority, assignment, etc.)."""
    _verify_tenant(claims, tenant_id)

    updates = {}
    if req.description is not None:
        updates["description"] = req.description.strip()
    if req.due_date is not None:
        updates["due_date"] = req.due_date.isoformat()
    if req.priority is not None:
        updates["priority"] = req.priority
    if req.status is not None:
        updates["status"] = req.status
    if req.assigned_to is not None:
        updates["assigned_to"] = req.assigned_to

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    result = (
        db.table("action_items")
        .update(updates)
        .eq("id", item_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Action item not found")
    return result.data[0]


@router.delete("/{tenant_id}/{item_id}")
async def delete_action_item(
    tenant_id: str,
    item_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete an action item."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    db.table("action_items").delete().eq("id", item_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}
