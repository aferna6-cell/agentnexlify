"""Widget chat conversation lookup, history load/save, response metrics.

Extracted from widget_chat_helpers.py (god class split 2026-05-24).
Re-exported via widget_chat_helpers so existing imports continue to resolve.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not add
a future-annotations import here.
"""

import logging

from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_upsert

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversation history helpers
# ---------------------------------------------------------------------------


def _get_or_create_conversation(
    tenant_id: str, session_id: str
) -> tuple[str, bool]:
    """Return (conversation_id, is_new).

    Looks up or creates a conversations row.  Message history is stored in the
    separate ``chat_messages`` table, not in conversations JSONB.

    If the insert fails, falls back to session_id — but downstream code must
    validate the conversation_id is a real UUID before using it for updates.
    """
    db = get_service_supabase()

    # Try to find an existing conversation
    try:
        result = (
            tenant_select(db, "conversations", tenant_id, "id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"], False
    except Exception:
        logger.warning("conversations lookup failed for session %s", session_id, exc_info=True)

    # Try to create one (upsert — safe against race conditions with unique constraint)
    try:
        new_conv = (
            tenant_upsert(
                db,
                "conversations",
                tenant_id,
                {"client_id": tenant_id, "session_id": session_id},
                on_conflict="client_id,session_id",
            )
            .execute()
        )
        if new_conv.data:
            return new_conv.data[0]["id"], True
        else:
            logger.error("conversations upsert returned no data for session %s tenant %s", session_id, tenant_id)
    except Exception:
        logger.error("conversations upsert FAILED for session %s tenant %s", session_id, tenant_id, exc_info=True)

    # Fallback: use session_id as a stable conversation identifier.
    # WARNING: This is NOT a UUID — downstream code must validate before DB updates.
    logger.warning("conversations fallback: using session_id %s as conversation_id (not a UUID)", session_id)
    return session_id, True


def _load_chat_history(
    tenant_id: str, session_id: str, limit: int = 20
) -> list[dict[str, str]]:
    """Load recent chat messages from the chat_messages table."""
    try:
        db = get_service_supabase()
        result = (
            tenant_select(db, "chat_messages", tenant_id, "role, content")
            .eq("session_id", session_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        msgs = [{"role": m["role"], "content": m["content"]} for m in (result.data or [])]
        logger.info(
            "chat_history: tenant=%s session=%s → %d messages loaded",
            tenant_id, session_id, len(msgs),
        )
        return msgs
    except Exception as e:
        logger.error(
            "chat_history FAILED: tenant=%s session=%s error=%s",
            tenant_id, session_id, e, exc_info=True,
        )
        # Retry without .order() in case created_at column is missing
        try:
            db = get_service_supabase()
            result = (
                tenant_select(db, "chat_messages", tenant_id, "role, content")
                .eq("session_id", session_id)
                .limit(limit)
                .execute()
            )
            msgs = [{"role": m["role"], "content": m["content"]} for m in (result.data or [])]
            logger.info("chat_history: retry without order succeeded, %d messages", len(msgs))
            return msgs
        except Exception as e2:
            logger.error("chat_history retry also FAILED: %s", e2, exc_info=True)
            return []


def _save_chat_messages(
    tenant_id: str, session_id: str, user_text: str | None, assistant_text: str | None
) -> None:
    """Persist user and/or assistant messages to chat_messages table."""
    try:
        db = get_service_supabase()
        rows = []
        if user_text:
            rows.append({"tenant_id": tenant_id, "session_id": session_id, "role": "user", "content": user_text})
        if assistant_text:
            rows.append({"tenant_id": tenant_id, "session_id": session_id, "role": "assistant", "content": assistant_text})
        if rows:
            tenant_insert(db, "chat_messages", tenant_id, rows).execute()
        logger.info("chat_save: OK tenant=%s session=%s msgs=%d", tenant_id, session_id, len(rows))
    except Exception as e:
        logger.error("chat_save FAILED: tenant=%s session=%s error=%s", tenant_id, session_id, e, exc_info=True)


# ---------------------------------------------------------------------------
# Response time metric recorder
# ---------------------------------------------------------------------------


def _record_response_metric(tenant_id: str, session_id: str, conversation_id: str) -> None:
    """Background task: record response time for the first message exchange."""
    try:
        db = get_service_supabase()
        messages = (
            tenant_select(db, "chat_messages", tenant_id, "role, created_at")
            .eq("session_id", session_id)
            .order("created_at")
            .limit(5)
            .execute()
        )
        if not messages.data or len(messages.data) < 2:
            return

        first_user = None
        first_response = None
        for msg in messages.data:
            if msg["role"] == "user" and not first_user:
                first_user = msg["created_at"]
            elif msg["role"] == "assistant" and first_user and not first_response:
                first_response = msg["created_at"]

        if not first_user or not first_response:
            return

        from datetime import datetime
        t1 = datetime.fromisoformat(first_user.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(first_response.replace("Z", "+00:00"))
        response_seconds = max(0, int((t2 - t1).total_seconds()))

        # Only pass conversation_id if it is a valid UUID.  _get_or_create_conversation
        # can fall back to returning session_id when the conversations table is unreachable.
        from uuid import UUID as _UUID
        try:
            _UUID(conversation_id or "")
            safe_conversation_id = conversation_id
        except (ValueError, AttributeError):
            logger.debug(
                "response_metric: conversation_id %r is not a UUID, omitting from insert",
                conversation_id,
            )
            safe_conversation_id = None

        tenant_insert(db, "response_metrics", tenant_id, {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "conversation_id": safe_conversation_id,
            "first_message_at": first_user,
            "first_response_at": first_response,
            "response_time_seconds": response_seconds,
            "channel": "widget",
        }).execute()
    except Exception:
        logger.error(
            "response_metric: failed for tenant %s session %s",
            tenant_id, session_id, exc_info=True,
        )
