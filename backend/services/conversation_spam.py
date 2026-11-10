"""Mark conversations as spam so they drop out of the shared inbox.

Spam is stored as a reserved ``spam`` entry in ``conversations.tags``
rather than in ``conversations.status``: production has
``conversations_status_check`` limiting status to active/completed/
handed_off, and the tags column needs no migration. Every writer of
``conversations.tags`` already merges into the existing list, so the
marker survives auto-tagging and handoff tagging.

Nothing here deletes data. Restoring removes the marker.
"""

import logging
from typing import Any, Iterable

from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update

logger = logging.getLogger(__name__)

SPAM_TAG = "spam"
# Roles allowed to mark, view, and restore spam. Plain members never see it.
SPAM_MANAGER_ROLES = ("owner", "admin")


def is_spam(tags: Iterable[str] | None) -> bool:
    return SPAM_TAG in (tags or [])


def can_manage_spam(claims: dict) -> bool:
    return claims.get("role", "owner") in SPAM_MANAGER_ROLES


def spam_session_ids(db: Any, tenant_id: str) -> set[str]:
    """Session ids of this tenant's conversations marked as spam.

    Fails open (empty set) so a metadata hiccup never blanks the inbox.
    """
    try:
        rows = tenant_select(db, "conversations", tenant_id, "session_id, tags").execute()
    except Exception:
        logger.warning("spam lookup failed for tenant %s", tenant_id, exc_info=True)
        return set()
    return {
        r["session_id"]
        for r in (rows.data or [])
        if r.get("session_id") and is_spam(r.get("tags"))
    }


def _find_row(db: Any, tenant_id: str, conversation_id: str) -> dict | None:
    for column in ("id", "session_id"):
        try:
            res = (
                tenant_select(db, "conversations", tenant_id, "id, session_id, tags")
                .eq(column, conversation_id)
                .limit(1)
                .execute()
            )
        except Exception:
            # A session_id is not a UUID; Postgres rejects it on the id column.
            continue
        if res.data:
            return res.data[0]
    return None


def _session_has_messages(db: Any, tenant_id: str, session_id: str) -> bool:
    res = (
        tenant_select(db, "chat_messages", tenant_id, "id")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def set_spam(db: Any, tenant_id: str, conversation_id: str, spam: bool) -> dict | None:
    """Mark (spam=True) or restore (spam=False) one conversation.

    ``conversation_id`` may be the conversations UUID or the session_id the
    inbox uses. Returns ``{"session_id", "spam", "tags"}`` or ``None`` when
    the conversation does not belong to this tenant (nothing is written).
    """
    row = _find_row(db, tenant_id, conversation_id)
    if row is None:
        # The inbox lists sessions straight from chat_messages, so a chat can
        # be visible without a conversations row. Create one to hold the mark.
        if not spam or not _session_has_messages(db, tenant_id, conversation_id):
            return None
        tenant_insert(
            db,
            "conversations",
            tenant_id,
            {"session_id": conversation_id, "tags": [SPAM_TAG]},
        ).execute()
        return {"session_id": conversation_id, "spam": True, "tags": [SPAM_TAG]}

    tags = [t for t in (row.get("tags") or []) if t != SPAM_TAG]
    if spam:
        tags.append(SPAM_TAG)
    tenant_update(db, "conversations", tenant_id, {"tags": tags}).eq("id", row["id"]).execute()
    return {"session_id": row.get("session_id"), "spam": spam, "tags": tags}
