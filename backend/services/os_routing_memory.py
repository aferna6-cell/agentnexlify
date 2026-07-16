"""Routing memory v1 — owner corrections become standing routing preferences.

When an owner re-routes a turn (the clarify picker or an explicit override),
the engine records it in ``os_routing_decision``: the corrected run carries
``decision='owner_override'`` with the picked ``chosen_agent``, and the
overridden prior row gets ``accepted=false`` + ``changed_to``. Until now that
signal was write-only — the classifier never read it back, so owners had to
repeat the same correction forever.

This module closes the loop deterministically (no LLM): before a turn goes to
the engine, a new ask that is highly similar to a previously corrected ask is
force-routed to the owner's corrected department. High precision over recall:
a wrong forced route is worse than letting the classifier decide, so the
similarity gate is strict (token Jaccard >= 0.7) and only known department
ids are honored.

WARNING: imported by modules FastAPI routers import — do NOT add
``from __future__ import annotations`` here.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# The 8 engine departments (agent-service departments.ts). A correction
# pointing anywhere else (retired v1 worker ids, junk) is never replayed.
KNOWN_DEPARTMENTS = frozenset(
    {
        "sales",
        "marketing",
        "customer_service",
        "operations",
        "invoicing",
        "accounting",
        "admin_records",
        "people",
    }
)

# Strict gate: only near-identical asks replay a correction.
SIMILARITY_THRESHOLD = 0.7
# Corrections older than this stop applying (businesses change).
MAX_AGE_DAYS = 90
_MAX_ROWS = 50

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = frozenset(
    "a an and are can could for i in is it me my of on our please that the "
    "them then this to us we with you your".split()
)


def _tokens(ask: str) -> frozenset:
    return frozenset(
        t for t in _TOKEN_RE.findall((ask or "").lower()) if t not in _STOPWORDS
    )


def _similarity(a: str, b: str) -> float:
    """Token Jaccard over stopword-filtered lowercase tokens. 0.0 when empty."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _correction_target(row: dict) -> str | None:
    """The department the owner corrected this ask TO, or None.

    Two teaching shapes: an overridden prior decision carries ``changed_to``;
    the corrected re-run carries ``decision='owner_override'`` with the picked
    agent in ``chosen_agent``.
    """
    changed_to = (row.get("changed_to") or "").strip()
    if changed_to:
        return changed_to
    if (row.get("decision") or "") == "owner_override":
        return (row.get("chosen_agent") or "").strip() or None
    return None


def learned_agent_for(db: Any, client_id: str, ask: str) -> str | None:
    """Department id the owner previously corrected a near-identical ask to.

    Reads recent routing corrections for this tenant (most recent first) and
    returns the first one whose ask clears the similarity gate and whose
    target is a known department. None on no match or any failure — the
    classifier always remains the fallback.
    """
    if not (ask or "").strip():
        return None
    try:
        since = (
            datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
        ).isoformat()
        rows = (
            db.table("os_routing_decision")
            .select("ask, decision, chosen_agent, changed_to, created_at")
            .eq("client_id", client_id)
            .gte("created_at", since)
            .or_("changed_to.not.is.null,decision.eq.owner_override")
            .order("created_at", desc=True)
            .limit(_MAX_ROWS)
            .execute()
        ).data or []

        for row in rows:
            target = _correction_target(row)
            if not target or target not in KNOWN_DEPARTMENTS:
                continue
            if _similarity(ask, row.get("ask") or "") >= SIMILARITY_THRESHOLD:
                logger.info(
                    "os_routing_memory: replaying owner correction "
                    "client_id=%s target=%s",
                    client_id,
                    target,
                )
                return target
        return None
    except Exception:
        logger.warning(
            "os_routing_memory: override lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return None


def resolve_force_agent(
    db: Any, client_id: str, ask: str, force_agent_id: str | None
) -> str | None:
    """Explicit override wins; otherwise the learned correction (or None)."""
    if force_agent_id:
        return force_agent_id
    return learned_agent_for(db, client_id, ask)
