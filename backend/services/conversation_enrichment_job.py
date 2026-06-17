"""Batch driver for conversation sentiment/intent enrichment.

There is no explicit "conversation closed" event in the widget chat flow (chats
are append-only into chat_messages), so enrichment runs as a periodic batch off
the user hot path. This job finds conversations that have gone idle and have not
been classified yet, then enriches each via
``conversation_enrichment.enrich_conversation``.

Kept separate from ``conversation_enrichment`` (single-conversation logic) so
the batch-selection concern lives in its own file. Registered in the scheduler
loop (backend/main.py, 30-min tier).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.conversation_enrichment import enrich_conversation

logger = logging.getLogger(__name__)

# A conversation is "settled" once it has had no new message for this long, so
# we classify a complete chat rather than one mid-stream.
_IDLE_MINUTES = 30
# Don't reach back further than this: old, never-classified rows are unlikely to
# matter and keep each batch bounded.
_LOOKBACK_HOURS = 48
# Cap conversations classified per batch tick so one run stays cheap.
_BATCH_CAP = 25


def _idle_before() -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=_IDLE_MINUTES)).isoformat()


def _lookback_after() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)).isoformat()


def _find_pending(db: Any) -> list[dict[str, Any]]:
    """Return idle, unclassified conversation rows (client_id + session_id).

    Cross-tenant by design: this is a service-role batch over all tenants. Each
    row still carries its own client_id, so the downstream enrich call stays
    tenant-scoped.
    """
    resp = (
        db.table("conversations")
        .select("client_id, session_id, last_message_at")
        .is_("sentiment", "null")
        .lte("last_message_at", _idle_before())
        .gte("last_message_at", _lookback_after())
        .order("last_message_at", desc=True)
        .limit(_BATCH_CAP)
        .execute()
    )
    return getattr(resp, "data", None) or []


async def run_pending_enrichment() -> str:
    """Classify a bounded batch of idle, unclassified conversations.

    Returns a short status string for the scheduler log. Degrades gracefully:
    a failure on one conversation is logged and the batch continues.
    """
    db = get_service_supabase()

    try:
        pending = _find_pending(db)
    except Exception:
        logger.warning("conversation_enrichment_job: pending lookup failed", exc_info=True)
        return "enrichment: lookup failed"

    if not pending:
        return "enrichment: nothing pending"

    classified = 0
    for row in pending:
        client_id = row.get("client_id")
        session_id = row.get("session_id")
        if not client_id or not session_id:
            continue
        try:
            result = await enrich_conversation(client_id, session_id, db=db)
        except Exception:
            logger.warning(
                "conversation_enrichment_job: enrich failed session=%s", session_id, exc_info=True
            )
            continue
        if result.get("sentiment") or result.get("intent"):
            classified += 1

    return f"enrichment: classified {classified}/{len(pending)} conversation(s)"
