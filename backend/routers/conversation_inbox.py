"""Shared team inbox — conversation assignment, internal notes, presence, team reply."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.activity import log_activity

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
        db.table("conversations")
        .select(select)
        .eq("id", conversation_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if conv.data:
        return conv.data[0]
    # Fallback: try session_id
    conv = (
        db.table("conversations")
        .select(select)
        .eq("session_id", conversation_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if conv.data:
        return conv.data[0]
    return None


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
    conv_row = _find_conversation(db, conversation_id, tenant_id)
    if not conv_row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_uuid = conv_row["id"]

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
        .eq("id", conv_uuid)
        .eq("client_id", tenant_id)
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
    # Resolve conversation_id (may be UUID or session_id from frontend)
    conv_row = _find_conversation(db, conversation_id, tenant_id)
    if not conv_row:
        return {"notes": []}
    conv_uuid = conv_row["id"]

    result = (
        db.table("conversation_notes")
        .select("*, team_members(name)")
        .eq("conversation_id", conv_uuid)
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
        "conversation_id": conv_uuid,
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
                db.table("team_members")
                .select("name")
                .eq("id", user_id)
                .eq("tenant_id", tenant_id)
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
            db.table("chat_messages")
            .insert({
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

        db.table("conversations").update({
            "messages": existing_messages,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", conversation["id"]).eq("client_id", tenant_id).execute()
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
        db.table("team_members").update({
            "last_active_conversation_id": conversation_id,
            "last_active_at": now,
        }).eq("id", team_member_id).eq("tenant_id", tenant_id).execute()
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
    five_min_ago = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()  # placeholder
    from datetime import timedelta
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    result = (
        db.table("team_members")
        .select("id, name, last_active_conversation_id, last_active_at")
        .eq("tenant_id", tenant_id)
        .gte("last_active_at", five_min_ago)
        .execute()
    )
    return {"active_members": result.data or []}


# ---------------------------------------------------------------------------
# Conversation Search
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/search")
async def search_conversations(
    tenant_id: str,
    q: str = "",
    limit: int = 50,
    claims: dict = Depends(_get_current_tenant),
):
    """Full-text search across chat_messages for a tenant.

    Searches message content using Supabase ilike (case-insensitive).
    Returns matching conversations with the matching message snippets.
    """
    _verify_tenant(claims, tenant_id)
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

    q = q.strip()
    if limit > 200:
        limit = 200

    db = get_supabase()

    # Search chat_messages for matching content
    try:
        messages_result = (
            db.table("chat_messages")
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .ilike("content", f"%{q}%")
            .order("created_at", desc=True)
            .limit(limit * 2)  # Over-fetch since we'll group by session
            .execute()
        )
    except Exception:
        logger.exception("search_conversations: chat_messages search failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Search failed")

    if not messages_result.data:
        return {"results": [], "query": q, "total": 0}

    # Group by session_id, keep first matching message per session
    seen_sessions = {}
    for msg in messages_result.data:
        sid = msg.get("session_id")
        if not sid or sid in seen_sessions:
            continue
        # Extract snippet around the match
        content = msg.get("content") or ""
        lower_content = content.lower()
        lower_q = q.lower()
        idx = lower_content.find(lower_q)
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(content), idx + len(q) + 60)
            snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
        else:
            snippet = content[:120] + ("..." if len(content) > 120 else "")

        seen_sessions[sid] = {
            "session_id": sid,
            "snippet": snippet,
            "role": msg.get("role"),
            "matched_at": msg.get("created_at"),
        }

        if len(seen_sessions) >= limit:
            break

    # Enrich with conversation metadata (lead info, tags)
    session_ids = list(seen_sessions.keys())
    if session_ids:
        try:
            convos = (
                db.table("conversations")
                .select("session_id, lead_id, tags, assigned_to")
                .eq("client_id", tenant_id)
                .in_("session_id", session_ids[:100])
                .execute()
            )
            conv_by_session = {c["session_id"]: c for c in (convos.data or [])}
        except Exception:
            logger.warning("search_conversations: failed to enrich with conversation data")
            conv_by_session = {}

        # Get lead names for conversations with lead_id
        lead_ids = [c.get("lead_id") for c in conv_by_session.values() if c.get("lead_id")]
        lead_names = {}
        if lead_ids:
            try:
                leads = (
                    db.table("leads")
                    .select("id, name, email")
                    .in_("id", lead_ids[:100])
                    .execute()
                )
                lead_names = {l["id"]: l for l in (leads.data or [])}
            except Exception:
                logger.warning("search_conversations: failed to fetch lead names")

        for sid, result in seen_sessions.items():
            conv = conv_by_session.get(sid, {})
            result["tags"] = conv.get("tags") or []
            result["assigned_to"] = conv.get("assigned_to")
            lead_id = conv.get("lead_id")
            if lead_id and lead_id in lead_names:
                result["lead_name"] = lead_names[lead_id].get("name")
                result["lead_email"] = lead_names[lead_id].get("email")

    results = list(seen_sessions.values())
    return {"results": results, "query": q, "total": len(results)}
