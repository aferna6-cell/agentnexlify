"""Conversation state management — load, create, and persist conversations.

Schema (conversations table):
  id, tenant_id, session_id, messages (JSONB), lead_id, started_at, last_message_at
"""


import logging

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)


def get_or_create_conversation(tenant_id: str, session_id: str) -> dict:
    """Find an existing conversation for this session or create a new one."""
    db = get_supabase()

    result = (
        db.table("conversations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]

    new_conv = {
        "tenant_id": tenant_id,
        "session_id": session_id,
        "messages": [],
    }
    try:
        result = db.table("conversations").insert(new_conv).execute()
        if result.data:
            return result.data[0]
    except Exception:
        logger.exception("Failed to create conversation for tenant %s", tenant_id)

    # Return a minimal dict so callers can continue even if DB insert fails
    return {"id": session_id, "tenant_id": tenant_id, "session_id": session_id, "messages": []}


