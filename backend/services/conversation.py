"""Conversation state management — load, create, and persist conversations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 50


def get_or_create_conversation(client_id: str, session_id: str, channel: str = "web") -> dict:
    """Find an active conversation for this session or create a new one."""
    db = get_supabase()
    result = (
        db.table("conversations")
        .select("*")
        .eq("client_id", client_id)
        .eq("session_id", session_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]

    new_conv = {
        "client_id": client_id,
        "session_id": session_id,
        "channel": channel,
        "status": "active",
    }
    result = db.table("conversations").insert(new_conv).execute()
    return result.data[0]


def load_message_history(conversation_id: str) -> list[dict[str, Any]]:
    """Load message history for a conversation, trimmed to the last N messages.

    Returns messages in the Anthropic API format:
    [{"role": "user"|"assistant", "content": ...}, ...]
    """
    db = get_supabase()
    result = (
        db.table("messages")
        .select("role, content, metadata")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    rows = result.data or []
    # Trim to last N messages
    if len(rows) > MAX_HISTORY_MESSAGES:
        rows = rows[-MAX_HISTORY_MESSAGES:]

    messages: list[dict[str, Any]] = []
    for row in rows:
        role = row["role"]
        content = row["content"]
        metadata = row.get("metadata") or {}

        if role in ("user", "assistant"):
            # Check if this assistant message had tool use blocks
            if role == "assistant" and metadata.get("tool_use_blocks"):
                # Reconstruct the content blocks
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
) -> dict:
    """Persist a message to the database."""
    db = get_supabase()
    msg = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "metadata": metadata,
    }
    result = db.table("messages").insert(msg).execute()

    # Update conversation timestamp
    db.table("conversations").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", conversation_id).execute()

    return result.data[0]


def get_conversation_messages(conversation_id: str) -> list[dict]:
    """Get raw messages for API response (chat history endpoint)."""
    db = get_supabase()
    result = (
        db.table("messages")
        .select("id, role, content, created_at, metadata")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []
