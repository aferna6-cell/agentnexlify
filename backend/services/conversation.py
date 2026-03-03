"""Conversation state management — load, create, and persist conversations.

Schema (conversations table):
  id, tenant_id, session_id, messages (JSONB), lead_id, started_at, last_message_at
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 50


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


def load_message_history(conversation_id: str) -> list[dict[str, Any]]:
    """Load message history from the JSONB messages column.

    Returns messages in Anthropic API format:
    [{"role": "user"|"assistant", "content": ...}, ...]
    """
    db = get_supabase()

    try:
        result = (
            db.table("conversations")
            .select("messages")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load conversation %s", conversation_id)
        return []

    if not result.data:
        return []

    raw_messages = result.data[0].get("messages") or []

    # Trim to last N messages
    if len(raw_messages) > MAX_HISTORY_MESSAGES:
        raw_messages = raw_messages[-MAX_HISTORY_MESSAGES:]

    messages: list[dict[str, Any]] = []
    for msg in raw_messages:
        role = msg.get("role")
        content = msg.get("content")
        metadata = msg.get("metadata") or {}

        if role in ("user", "assistant"):
            # Reconstruct tool_use blocks if present
            if role == "assistant" and metadata.get("tool_use_blocks"):
                blocks: list[dict] = [{"type": "text", "text": content}] if content else []
                for tb in metadata["tool_use_blocks"]:
                    blocks.append({
                        "type": "tool_use",
                        "id": tb["id"],
                        "name": tb["name"],
                        "input": tb["input"],
                    })
                messages.append({"role": "assistant", "content": blocks})
            else:
                messages.append({"role": role, "content": content})
        elif role == "tool_result":
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": metadata.get("tool_use_id", ""),
                        "content": content,
                    }
                ],
            })

    return messages


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a message to the JSONB messages array on the conversation row."""
    db = get_supabase()

    msg_entry: dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        msg_entry["metadata"] = metadata

    try:
        # Load current messages, append, and save back
        result = (
            db.table("conversations")
            .select("messages")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.warning("Conversation %s not found — cannot save message", conversation_id)
            return

        current_messages = result.data[0].get("messages") or []
        current_messages.append(msg_entry)

        db.table("conversations").update({
            "messages": current_messages,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", conversation_id).execute()
    except Exception:
        logger.exception("Failed to save message to conversation %s", conversation_id)


def get_conversation_messages(conversation_id: str) -> list[dict]:
    """Get raw messages for API response (chat history endpoint)."""
    db = get_supabase()

    try:
        result = (
            db.table("conversations")
            .select("messages")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to get messages for conversation %s", conversation_id)
        return []

    if not result.data:
        return []

    messages = result.data[0].get("messages") or []

    # Filter to user/assistant messages for display
    return [
        {
            "role": m["role"],
            "content": m["content"],
            "timestamp": m.get("timestamp"),
        }
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
