"""Customer memory for widget chat (suite item 5 — Memory Bank analog, v1).

A returning visitor should not start cold. This derives a compact profile
from data we already store - the session's conversation row and its linked
lead - and hands the widget a short system-prompt block: name, prior visit
recency, status, interests. Deterministic reads only; every failure returns
None so chat never degrades. leads/conversations use client_id per schema
discipline.
"""

import logging

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_MAX_BLOCK = 600


def profile_block(db, tenant_id: str, session_id: str | None) -> str | None:
    """A short 'returning customer' block for the system prompt, or None."""
    if not session_id:
        return None
    try:
        convo_rows = (
            tenant_select(
                db,
                "conversations",
                tenant_id,
                "session_id, lead_id, created_at, last_message_at",
            )
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "customer_memory: conversation read failed tenant=%s", tenant_id,
            exc_info=True,
        )
        return None
    if not convo_rows:
        return None
    convo = convo_rows[0]

    lead = None
    lead_id = convo.get("lead_id")
    if lead_id:
        try:
            lead_rows = (
                tenant_select(
                    db,
                    "leads",
                    tenant_id,
                    "name, status, areas_of_interest, created_at",
                )
                .eq("id", lead_id)
                .limit(1)
                .execute()
            ).data or []
            lead = lead_rows[0] if lead_rows else None
        except Exception:
            logger.warning(
                "customer_memory: lead read failed tenant=%s", tenant_id,
                exc_info=True,
            )

    parts: list[str] = []
    first_seen = str(convo.get("created_at") or "")[:10]
    if first_seen:
        parts.append(f"This visitor has chatted before (first seen {first_seen}).")
    if lead:
        name = (lead.get("name") or "").strip()
        if name:
            parts.append(f"They are a known lead: {name}.")
        status = (lead.get("status") or "").strip()
        if status:
            parts.append(f"Lead status: {status}.")
        interests = lead.get("areas_of_interest")
        if isinstance(interests, list) and interests:
            parts.append(
                "Previously interested in: "
                + ", ".join(str(i) for i in interests[:5]) + "."
            )
    if not parts:
        return None
    block = (
        "RETURNING CUSTOMER CONTEXT (from your records - greet them like you "
        "remember them, and do not re-ask for details listed here): "
        + " ".join(parts)
    )
    return block[:_MAX_BLOCK]
