"""AI-generated conversation summary helpers for leads.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. The AI call itself stays in the router so the
handler remains async; this module owns the DB lookups, transcript shaping,
and persistence.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_MESSAGES = 30
MIN_MESSAGES_TO_SUMMARIZE = 2
TRANSCRIPT_CHAR_LIMIT = 3000


def fetch_lead_summary_inputs(
    db: Any, tenant_id: str, lead_id: str
) -> list[dict]:
    """Return the conversation messages a lead summary should be built from.

    Raises:
        LookupError("not_found"): lead does not exist for tenant.
        LookupError("no_conversation"): lead has no linked conversation.
        LookupError("no_messages"): conversation exists but has no messages.
        LookupError("too_short"): conversation has fewer than MIN messages.
    """
    lead_resp = (
        tenant_select(db, "leads", tenant_id, "conversation_id, name")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead_resp.data:
        raise LookupError("not_found")

    conv_id = lead_resp.data[0].get("conversation_id")
    if not conv_id:
        raise LookupError("no_conversation")

    conv_resp = (
        tenant_select(db, "conversations", tenant_id, "messages")
        .eq("id", conv_id)
        .limit(1)
        .execute()
    )
    if not conv_resp.data or not conv_resp.data[0].get("messages"):
        raise LookupError("no_messages")

    messages = conv_resp.data[0]["messages"]
    if len(messages) < MIN_MESSAGES_TO_SUMMARIZE:
        raise LookupError("too_short")

    return messages


def build_lead_transcript(
    messages: list[dict],
    *,
    limit: int = MAX_TRANSCRIPT_MESSAGES,
    char_limit: int = TRANSCRIPT_CHAR_LIMIT,
) -> str:
    """Render the last `limit` messages as a `Visitor:`/`Agent:` transcript.

    Trims the output to `char_limit` characters before returning.
    """
    transcript = "\n".join(
        f"{'Visitor' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in messages[-limit:]
    )
    return transcript[:char_limit]


def save_lead_summary(
    db: Any, tenant_id: str, lead_id: str, summary: str
) -> None:
    """Persist an AI-generated summary on the lead row."""
    tenant_update(
        db, "leads", tenant_id, {"conversation_summary": summary}
    ).eq("id", lead_id).execute()
