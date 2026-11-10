"""Conversation list, detail, and tag-upsert service."""

import logging

from fastapi import HTTPException

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.conversation_spam import SPAM_TAG, is_spam, spam_session_ids

logger = logging.getLogger(__name__)


def _get_db():
    return _get_service_supabase()


def list_conversations(
    tenant_id: str,
    channel: str | None = None,
    search: str | None = None,
    view: str = "inbox",
) -> dict:
    """Return the conversation list with lead name enrichment.

    ``view="inbox"`` (default) hides conversations marked as spam;
    ``view="spam"`` returns only those, so they can be restored.
    """
    db = _get_db()
    spam_ids = spam_session_ids(db, tenant_id)
    if view == "spam" and not spam_ids:
        return {"conversations": [], "spam_count": 0}
    msg_query = (
        db.table("chat_messages")
        .select("session_id, role, content, created_at")
        .eq("tenant_id", tenant_id)
    )
    if view == "spam":
        msg_query = msg_query.in_("session_id", sorted(spam_ids))
    result = msg_query.order("created_at", desc=True).limit(500).execute()
    messages = result.data or []
    if view != "spam" and spam_ids:
        messages = [m for m in messages if m["session_id"] not in spam_ids]

    sessions: dict = {}
    for msg in messages:
        sid = msg["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "message_count": 0,
                "last_message": "",
                "last_message_at": msg["created_at"],
                "preview": "",
            }
        sessions[sid]["message_count"] += 1
        if msg["role"] == "user" and not sessions[sid]["preview"]:
            sessions[sid]["preview"] = (msg["content"] or "")[:120]
        if msg["created_at"] >= sessions[sid]["last_message_at"]:
            sessions[sid]["last_message_at"] = msg["created_at"]
            sessions[sid]["last_message"] = (msg["content"] or "")[:120]

    lead_map: dict = {}
    lead_id_map: dict = {}
    try:
        leads_result = (
            db.table("leads")
            .select("id, conversation_id, name, email")
            .eq("client_id", tenant_id)
            .execute()
        )
        for lead in leads_result.data or []:
            cid = lead.get("conversation_id")
            if cid:
                lead_map[cid] = lead.get("name") or lead.get("email") or ""
                lead_id_map[cid] = lead["id"]
    except Exception:
        logger.warning(
            "Failed to map lead names to conversations for tenant %s",
            tenant_id,
            exc_info=True,
        )

    tags_map: dict = {}
    channel_map: dict = {}
    assigned_map: dict = {}
    try:
        conv_query = (
            db.table("conversations")
            .select("session_id, tags, channel, assigned_to")
            .eq("client_id", tenant_id)
        )
        if channel:
            conv_query = conv_query.eq("channel", channel)
        conv_result = conv_query.execute()
        for conv in conv_result.data or []:
            sid = conv.get("session_id")
            if sid:
                if conv.get("tags"):
                    tags_map[sid] = conv["tags"]
                channel_map[sid] = conv.get("channel") or "widget"
                if conv.get("assigned_to"):
                    assigned_map[sid] = conv["assigned_to"]
    except Exception:
        logger.warning(
            "Failed to fetch conversation metadata for tenant %s",
            tenant_id,
            exc_info=True,
        )

    conv_list = sorted(
        sessions.values(), key=lambda s: s["last_message_at"], reverse=True
    )

    if search:
        search_lower = search.lower()
        matching_sessions: set = set()
        for msg in messages:
            if search_lower in (msg.get("content") or "").lower():
                matching_sessions.add(msg["session_id"])
        for sid, name in lead_map.items():
            if search_lower in (name or "").lower():
                matching_sessions.add(sid)
        conv_list = [c for c in conv_list if c["session_id"] in matching_sessions]

    if channel:
        channel_session_ids = set(channel_map.keys())
        conv_list = [c for c in conv_list if c["session_id"] in channel_session_ids]

    for c in conv_list:
        c["lead_name"] = lead_map.get(c["session_id"], "")
        c["lead_id"] = lead_id_map.get(c["session_id"])
        c["tags"] = tags_map.get(c["session_id"], [])
        c["channel"] = channel_map.get(c["session_id"], "widget")
        c["assigned_to"] = assigned_map.get(c["session_id"])
        c["is_spam"] = c["session_id"] in spam_ids

    return {"conversations": conv_list, "spam_count": len(spam_ids)}


def get_conversation_messages(
    tenant_id: str, session_id: str, include_spam: bool = True
) -> dict:
    """Return messages for a single conversation session.

    With ``include_spam=False`` a spam-marked session reads as not found.
    """
    db = _get_db()
    if not include_spam and session_id in spam_session_ids(db, tenant_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = (
        db.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"messages": result.data or []}


def update_conversation_tags(tenant_id: str, session_id: str, tags: list) -> dict:
    """Upsert tags on a conversation row. Uses client_id (conversations table rule)."""
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be a list")
    # The spam marker is owned by the spam endpoints (owner/admin only); the
    # tag editor can neither add nor drop it.
    tags = [str(t)[:30] for t in tags if isinstance(t, str) and t != SPAM_TAG][:10]

    db = _get_db()
    existing = (
        db.table("conversations")
        .select("id, tags")
        .eq("client_id", tenant_id)
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    if existing.data and is_spam(existing.data[0].get("tags")):
        tags = tags + [SPAM_TAG]
    if existing.data:
        db.table("conversations").update({"tags": tags}).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        db.table("conversations").insert(
            {
                "client_id": tenant_id,
                "session_id": session_id,
                "tags": tags,
            }
        ).execute()

    return {"session_id": session_id, "tags": tags}
