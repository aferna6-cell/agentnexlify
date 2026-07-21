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


# --------------------------------------------------------------------------
# Phase 2 - memory write-back (propose-only).
#
# Deterministic: recent chats where a known lead mentioned one of the
# tenant's service types that is NOT yet on their lead record become ONE
# opportunity suggestion. Nothing is written to the lead until the owner
# accepts; acceptance re-derives the same findings and appends them to
# leads.areas_of_interest (see os_opportunity_fulfill).
# --------------------------------------------------------------------------

_WRITEBACK_WINDOW_HOURS = 24
_WRITEBACK_CONVO_CAP = 20
_WRITEBACK_MSG_CAP = 30
_MIN_SERVICE_NAME_LEN = 4

WRITEBACK_SUMMARY_PREFIX = "Remember new customer interests"


def _service_names(db, tenant_id: str) -> list[str]:
    try:
        rows = (
            tenant_select(db, "service_types", tenant_id, "name")
            .limit(100)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "customer_memory: service_types read failed tenant=%s", tenant_id,
            exc_info=True,
        )
        return []
    names = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        if len(name) >= _MIN_SERVICE_NAME_LEN:
            names.append(name)
    return names


def detect_interest_writebacks(db, tenant_id: str) -> list[dict]:
    """Leads whose recent chats mention services missing from their record.

    Returns [{lead_id, lead_name, new_interests}]. Deterministic substring
    match against the tenant's own service-type names - no LLM, no guesses.
    [] on any failure.
    """
    from datetime import datetime, timedelta, timezone

    services = _service_names(db, tenant_id)
    if not services:
        return []
    since = (
        datetime.now(timezone.utc) - timedelta(hours=_WRITEBACK_WINDOW_HOURS)
    ).isoformat()
    try:
        convos = (
            tenant_select(db, "conversations", tenant_id, "session_id, lead_id")
            .not_.is_("lead_id", "null")
            .gte("last_message_at", since)
            .limit(_WRITEBACK_CONVO_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "customer_memory: writeback convo read failed tenant=%s", tenant_id,
            exc_info=True,
        )
        return []

    findings: list[dict] = []
    for convo in convos:
        lead_id = convo.get("lead_id")
        session_id = convo.get("session_id")
        if not lead_id or not session_id:
            continue
        try:
            lead_rows = (
                tenant_select(db, "leads", tenant_id, "id, name, areas_of_interest")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            ).data or []
            msg_rows = (
                tenant_select(db, "chat_messages", tenant_id, "role, content")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(_WRITEBACK_MSG_CAP)
                .execute()
            ).data or []
        except Exception:
            continue
        if not lead_rows:
            continue
        lead = lead_rows[0]
        existing = {
            str(i).strip().lower()
            for i in (lead.get("areas_of_interest") or [])
            if str(i).strip()
        }
        visitor_text = " ".join(
            str(m.get("content") or "")
            for m in msg_rows
            if (m.get("role") or "") == "user"
        ).lower()
        if not visitor_text:
            continue
        new_interests = [
            s
            for s in services
            if s.lower() in visitor_text and s.lower() not in existing
        ]
        if new_interests:
            findings.append(
                {
                    "lead_id": lead["id"],
                    "lead_name": (lead.get("name") or "").strip() or "Unknown lead",
                    "new_interests": new_interests[:5],
                }
            )
    return findings


def writeback_suggestion(findings: list[dict]) -> dict | None:
    """One propose-only suggestion covering every finding, or None."""
    if not findings:
        return None
    lines = [
        f"{f['lead_name']}: {', '.join(f['new_interests'])}" for f in findings[:10]
    ]
    return {
        "summary": (
            f"{WRITEBACK_SUMMARY_PREFIX} from recent chats "
            f"({len(findings)} lead{'s' if len(findings) != 1 else ''})"
        ),
        "detail": (
            "These customers mentioned services in chat that are not on "
            "their lead record yet. Accept to add the interests so future "
            "conversations and follow-ups remember them.\n"
            + "\n".join(lines)
        ),
    }


def apply_interest_writebacks(db, tenant_id: str) -> int:
    """Append detected interests to leads. Called ONLY after owner accept.

    Re-derives findings at accept time (suggestion rows carry no metadata),
    the same recompute-on-accept pattern the other opportunity kinds use.
    Returns leads updated.
    """
    findings = detect_interest_writebacks(db, tenant_id)
    updated = 0
    for finding in findings:
        try:
            lead_rows = (
                tenant_select(db, "leads", tenant_id, "id, areas_of_interest")
                .eq("id", finding["lead_id"])
                .limit(1)
                .execute()
            ).data or []
            if not lead_rows:
                continue
            current = [
                str(i) for i in (lead_rows[0].get("areas_of_interest") or [])
            ]
            existing_lower = {i.strip().lower() for i in current}
            merged = current + [
                i for i in finding["new_interests"]
                if i.strip().lower() not in existing_lower
            ]
            if len(merged) == len(current):
                continue
            from backend.services.tenant_scope import tenant_update

            tenant_update(
                db, "leads", tenant_id, {"areas_of_interest": merged}
            ).eq("id", finding["lead_id"]).execute()
            updated += 1
        except Exception:
            logger.warning(
                "customer_memory: writeback apply failed lead=%s tenant=%s",
                finding.get("lead_id"),
                tenant_id,
                exc_info=True,
            )
    return updated
