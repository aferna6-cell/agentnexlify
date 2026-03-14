"""Shared team inbox — conversation assignment + internal notes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])


class AssignRequest(BaseModel):
    assigned_to: str | None = None  # team_member UUID, null to unassign


class NoteCreate(BaseModel):
    content: str = Field(..., max_length=2000)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Conversation Assignment ---

@router.put("/{tenant_id}/conversations/{conversation_id}/assign")
async def assign_conversation(
    tenant_id: str,
    conversation_id: str,
    req: AssignRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Assign or unassign a conversation to a team member."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify conversation belongs to tenant
    conv = (
        db.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # If assigning, verify team member exists
    assignee_name = None
    if req.assigned_to:
        member = (
            db.table("team_members")
            .select("id, name")
            .eq("id", req.assigned_to)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=404, detail="Team member not found")
        assignee_name = member.data[0].get("name", "Team member")

    # Update assignment
    result = (
        db.table("conversations")
        .update({"assigned_to": req.assigned_to})
        .eq("id", conversation_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    # Log activity
    action = f"Assigned to {assignee_name}" if req.assigned_to else "Unassigned"
    try:
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "activity_type": "conversation_assigned",
            "description": action,
        }).execute()
    except Exception:
        logger.warning("Failed to log conversation assignment activity", exc_info=True)

    return {"assigned_to": req.assigned_to, "message": action}


# --- Internal Notes ---

@router.get("/{tenant_id}/conversations/{conversation_id}/notes")
async def list_notes(
    tenant_id: str,
    conversation_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List internal notes for a conversation. Team-only, never visible to customers."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("conversation_notes")
        .select("*, team_members(name)")
        .eq("conversation_id", conversation_id)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"notes": result.data or []}


@router.post("/{tenant_id}/conversations/{conversation_id}/notes")
async def create_note(
    tenant_id: str,
    conversation_id: str,
    req: NoteCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Add an internal note to a conversation."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Get team member ID from claims
    team_member_id = claims.get("team_member_id")
    if not team_member_id:
        # Owner might not have a team_member record — use tenant owner
        owner = (
            db.table("team_members")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("role", "owner")
            .limit(1)
            .execute()
        )
        if owner.data:
            team_member_id = owner.data[0]["id"]
        else:
            raise HTTPException(status_code=400, detail="Could not identify note author")

    data = {
        "conversation_id": conversation_id,
        "tenant_id": tenant_id,
        "author_id": team_member_id,
        "content": req.content.strip(),
    }
    result = db.table("conversation_notes").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create note")
    return result.data[0]


@router.delete("/{tenant_id}/notes/{note_id}")
async def delete_note(
    tenant_id: str,
    note_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete an internal note."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    db.table("conversation_notes").delete().eq("id", note_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}
