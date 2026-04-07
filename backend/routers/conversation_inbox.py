"""Shared team inbox — conversation assignment, internal notes, presence, team reply."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.activity import log_activity
from backend.services.tenant_scope import tenant_delete, tenant_insert, tenant_select, tenant_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])


class AssignRequest(BaseModel):
    assigned_to: str | None = None  # team_member UUID, null to unassign


class NoteCreate(BaseModel):
    content: str = Field(..., max_length=2000)


class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _find_conversation(db, conversation_id: str, tenant_id: str, select: str = "id"):
    """Look up a conversation by UUID id or session_id (frontend passes session_id)."""
    conv = (
        tenant_select(db, "conversations", tenant_id, select)
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    if conv.data:
        return conv.data[0]
    # Fallback: try session_id
    conv = (
        tenant_select(db, "conversations", tenant_id, select)
        .eq("session_id", conversation_id)
        .limit(1)
        .execute()
    )
    if conv.data:
        return conv.data[0]
    return None


# --- Conversation Assignment Notification ---

async def _send_assignment_notification(
    tenant_id: str,
    assignee_name: str,
    assignee_email: str,
    conversation_preview: str,
    lead_name: str,
) -> None:
    """Email team member when a conversation is assigned to them.

    Best-effort: failures are logged but don't block the assignment.
    """
    if not assignee_email:
        return

    try:
        from backend.services.email_sender import send_email
        from backend.config import settings

        dashboard_url = settings.frontend_url.rstrip("/")
        preview_text = conversation_preview[:200] if conversation_preview else "(no messages yet)"

        body_html = (
            f"<h2>Conversation Assigned to You</h2>"
            f"<p>Hi {assignee_name},</p>"
            f"<p>A conversation has been assigned to you.</p>"
            f'<div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:16px 0;">'
            f'<p style="margin:4px 0;"><strong>Lead:</strong> {lead_name or "Unknown visitor"}</p>'
            f'<p style="margin:4px 0;"><strong>Latest message:</strong></p>'
            f'<p style="margin:4px 0;color:#6b7280;font-style:italic;">"{preview_text}"</p>'
            f"</div>"
            f'<p><a href="{dashboard_url}/conversations" '
            f'style="color:#2563eb;text-decoration:underline;">'
            f"Open in Dashboard</a></p>"
        )

        await send_email(
            to=assignee_email,
            subject="Conversation assigned to you",
            body_html=body_html,
            tenant_id=tenant_id,
        )
        logger.info("Sent assignment notification to %s for tenant %s", assignee_email, tenant_id)
    except Exception:
        logger.warning(
            "Failed to send assignment notification to %s", assignee_email, exc_info=True
        )


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

    # Verify conversation belongs to tenant (supports UUID or session_id)
    conv_row = _find_conversation(db, conversation_id, tenant_id, select="id, session_id, lead_id")
    if not conv_row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_uuid = conv_row["id"]

    # If assigning, verify team member exists
    assignee_name = None
    assignee_email = None
    if req.assigned_to:
        member = (
            tenant_select(db, "team_members", tenant_id, "id, name, email")
            .eq("id", req.assigned_to)
            .limit(1)
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=404, detail="Team member not found")
        assignee_name = member.data[0].get("name", "Team member")
        assignee_email = member.data[0].get("email")

    # Update assignment
    result = (
        tenant_update(db, "conversations", tenant_id, {"assigned_to": req.assigned_to})
        .eq("id", conv_uuid)
        .execute()
    )

    # Log activity
    action = f"Assigned to {assignee_name}" if req.assigned_to else "Unassigned"
    try:
        tenant_insert(db, "activity_log", tenant_id, {
            "tenant_id": tenant_id,
            "activity_type": "conversation_assigned",
            "description": action,
        }).execute()
    except Exception:
        logger.warning("Failed to log conversation assignment activity", exc_info=True)

    # Send email notification to assigned team member (only on assign, not unassign)
    if req.assigned_to and assignee_email:
        # Get conversation preview for notification
        conversation_preview = ""
        lead_name = ""
        try:
            session_id = conv_row.get("session_id")
            if session_id:
                last_msg = (
                    tenant_select(db, "chat_messages", tenant_id, "content, role")
                    .eq("session_id", session_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if last_msg.data:
                    conversation_preview = last_msg.data[0].get("content", "")

            # Get lead name if available
            lead_id = conv_row.get("lead_id")
            if lead_id:
                lead_row = (
                    tenant_select(db, "leads", tenant_id, "name")
                    .eq("id", lead_id)
                    .limit(1)
                    .execute()
                )
                if lead_row.data:
                    lead_name = lead_row.data[0].get("name", "")
        except Exception:
            logger.warning("Failed to fetch conversation preview for notification", exc_info=True)

        await _send_assignment_notification(
            tenant_id=tenant_id,
            assignee_name=assignee_name,
            assignee_email=assignee_email,
            conversation_preview=conversation_preview,
            lead_name=lead_name,
        )

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
    # Resolve conversation_id (may be UUID or session_id from frontend)
    conv_row = _find_conversation(db, conversation_id, tenant_id)
    if not conv_row:
        return {"notes": []}
    conv_uuid = conv_row["id"]

    result = (
        tenant_select(db, "conversation_notes", tenant_id, "*, team_members(name)")
        .eq("conversation_id", conv_uuid)
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

    # Resolve conversation_id (may be UUID or session_id from frontend)
    conv_row = _find_conversation(db, conversation_id, tenant_id)
    if not conv_row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_uuid = conv_row["id"]

    # Get team member ID from claims
    team_member_id = claims.get("team_member_id")
    if not team_member_id:
        # Owner might not have a team_member record — use tenant owner
        owner = (
            tenant_select(db, "team_members", tenant_id, "id")
            .eq("role", "owner")
            .limit(1)
            .execute()
        )
        if owner.data:
            team_member_id = owner.data[0]["id"]
        else:
            raise HTTPException(status_code=400, detail="Could not identify note author")

    data = {
        "conversation_id": conv_uuid,
        "tenant_id": tenant_id,
        "author_id": team_member_id,
        "content": req.content.strip(),
    }
    result = tenant_insert(db, "conversation_notes", tenant_id, data).execute()
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
    tenant_delete(db, "conversation_notes", tenant_id).eq("id", note_id).execute()
    return {"deleted": True}


# --- Team Reply ---

def _resolve_replier_name(claims: dict, db, tenant_id: str) -> str:
    """Determine the name of the team member sending a reply.

    Checks JWT claims first (``name`` field), then falls back to a DB
    lookup in ``team_members``.  If nothing is found, uses the email
    address from the claims.
    """
    # JWT 'name' claim (set for team members on login)
    if claims.get("name"):
        return claims["name"]

    # Fallback: look up by user_id (team_member id) in the JWT
    user_id = claims.get("user_id")
    if user_id:
        try:
            member = (
                tenant_select(db, "team_members", tenant_id, "name")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if member.data and member.data[0].get("name"):
                return member.data[0]["name"]
        except Exception:
            logger.warning("Failed to look up team member name for %s", user_id, exc_info=True)

    # Last resort — use the email
    return claims.get("email", "Team member")


@router.post("/{tenant_id}/conversations/{conversation_id}/reply")
async def reply_to_conversation(
    tenant_id: str,
    conversation_id: str,
    req: ReplyCreate,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Send a team reply to a customer conversation.

    The reply is inserted into ``chat_messages`` with role ``assistant``
    so the widget shows it as a bot/team message.  The conversation's
    JSONB ``messages`` array is also updated for legacy compatibility.
    """
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # 1. Verify conversation belongs to tenant and get session_id (supports UUID or session_id)
    try:
        conversation = _find_conversation(db, conversation_id, tenant_id, select="id, session_id, messages, lead_id")
    except Exception as e:
        logger.error("reply: conversation lookup failed conv=%s tenant=%s: %s", conversation_id, tenant_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to look up conversation")

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session_id = conversation.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Conversation has no session_id")

    reply_content = req.content.strip()

    # 2. Insert into chat_messages with role "assistant"
    try:
        msg_result = (
            tenant_insert(db, "chat_messages", tenant_id, {
                "tenant_id": tenant_id,
                "session_id": session_id,
                "role": "assistant",
                "content": reply_content,
            })
            .execute()
        )
    except Exception as e:
        logger.error("reply: chat_messages insert failed session=%s tenant=%s: %s", session_id, tenant_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save reply message")

    if not msg_result.data:
        raise HTTPException(status_code=500, detail="Failed to save reply message")

    created_message = msg_result.data[0]

    # 3. Append to conversations.messages JSONB array (legacy format)
    try:
        existing_messages = conversation.get("messages") or []
        if isinstance(existing_messages, str):
            existing_messages = json.loads(existing_messages)

        existing_messages.append({
            "role": "assistant",
            "content": reply_content,
        })

        tenant_update(db, "conversations", tenant_id, {
            "messages": existing_messages,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", conversation["id"]).execute()
    except Exception:
        # Non-fatal: chat_messages is the canonical store.
        # The conversations JSONB is legacy and unreliable.
        logger.warning(
            "reply: conversations JSONB update failed conv=%s, chat_messages insert succeeded",
            conversation_id, exc_info=True,
        )

    # 4. Log activity
    replier_name = _resolve_replier_name(claims, db, tenant_id)
    lead_id = conversation.get("lead_id")
    log_activity(
        tenant_id=tenant_id,
        activity_type="team_reply",
        description=f"Team reply by {replier_name}",
        lead_id=str(lead_id) if lead_id else None,
    )

    logger.info(
        "reply: OK tenant=%s conv=%s session=%s by=%s",
        tenant_id, conversation_id, session_id, replier_name,
    )

    return {
        "message": created_message,
        "session_id": session_id,
        "replied_by": replier_name,
    }


# --- Presence Tracking ---

@router.put("/{tenant_id}/presence")
async def update_presence(
    tenant_id: str,
    conversation_id: str | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Update which conversation the current team member is viewing.
    Called by the frontend when opening a conversation. Pass null to clear."""
    _verify_tenant(claims, tenant_id)

    team_member_id = claims.get("team_member_id")
    if not team_member_id:
        return {"ok": True}  # Owner without team_member record — skip

    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    try:
        tenant_update(db, "team_members", tenant_id, {
            "last_active_conversation_id": conversation_id,
            "last_active_at": now,
        }).eq("id", team_member_id).execute()
    except Exception:
        logger.warning("Presence update failed for member %s", team_member_id, exc_info=True)

    return {"ok": True}


@router.get("/{tenant_id}/presence")
async def get_presence(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get which team members are currently active and which conversations they're viewing."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    # Consider "active" if last_active_at is within the last 5 minutes
    from datetime import timedelta
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    result = (
        tenant_select(db, "team_members", tenant_id, "id, name, last_active_conversation_id, last_active_at")
        .gte("last_active_at", five_min_ago)
        .execute()
    )
    return {"active_members": result.data or []}
