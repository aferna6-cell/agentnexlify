"""Proactive opportunity scan — the AI staff notices things (gap G7).

Deterministic-first: two rules, no LLM.
  1. Cold leads — warm/hot leads with no activity for 7+ days.
  2. Overdue invoices — status 'sent' past their due date.

Each finding becomes an os_backlog_requests row (reason='opportunity') so it
lands in the owner's existing review flow — suggestions only, never
auto-executed. Nightly job dedupes per tenant: an open suggestion with the
same summary is not re-filed.

Schema notes: leads/conversations use client_id; invoices/appointments use
tenant_id (see .claude/rules/schema-discipline.md).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services import os_opportunity_notify

logger = logging.getLogger(__name__)

_COLD_DAYS = 7
_MAX_COLD_LEADS_NAMED = 3
_TENANT_BATCH = 200


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suggestion_kind(summary: str) -> str | None:
    """Classify a suggestion by the wording our own scanner produces.

    Same dispatch the fulfillment side uses
    (``os_opportunity_fulfill.fulfill_accepted_suggestion``) — both strings
    are generated and consumed inside this codebase.
    """
    s = (summary or "").lower()
    if "lead" in s and "cold" in s:
        return "cold_leads"
    if "invoice" in s:
        return "overdue_invoices"
    if "remember" in s and "interest" in s:
        return "memory_writeback"
    return None


def compute_suggestions(db: Any, client_id: str) -> list[dict[str, Any]]:
    """Deterministic suggestion list for one tenant. [] on any failure."""
    suggestions: list[dict[str, Any]] = []

    # Rule 1 — leads gone cold (still open, untouched for 7+ days)
    try:
        cold = (
            db.table("leads")
            .select("id, name, updated_at")
            .eq("client_id", client_id)
            .in_("lead_temperature", ["warm", "hot"])
            .lt("updated_at", _iso_days_ago(_COLD_DAYS))
            .limit(25)
            .execute()
        ).data or []
        if cold:
            names = [l.get("name") or "Unnamed lead" for l in cold[:_MAX_COLD_LEADS_NAMED]]
            extra = len(cold) - len(names)
            who = ", ".join(names) + (f" and {extra} more" if extra > 0 else "")
            suggestions.append(
                {
                    "summary": f"{len(cold)} lead{'s' if len(cold) != 1 else ''} went cold this week — want me to follow up?",
                    "detail": (
                        f"No activity for {_COLD_DAYS}+ days on: {who}. "
                        "Accept and I'll draft a friendly check-in for each "
                        "(you approve every message before it sends)."
                    ),
                }
            )
    except Exception:
        logger.warning("os_opportunities: cold-lead scan failed for %s", client_id, exc_info=True)

    # Rule 2 — overdue invoices
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        overdue = (
            db.table("invoices")
            .select("id, invoice_number, total, due_date")
            .eq("tenant_id", client_id)
            .eq("status", "sent")
            .lt("due_date", today)
            .limit(25)
            .execute()
        ).data or []
        if overdue:
            total = sum(float(i.get("total") or 0) for i in overdue)
            suggestions.append(
                {
                    "summary": f"{len(overdue)} unpaid invoice{'s' if len(overdue) != 1 else ''} (${total:,.0f}) past due — want me to send reminders?",
                    "detail": (
                        "Accept and I'll draft a polite payment reminder for each "
                        "overdue invoice (you approve before anything sends)."
                    ),
                }
            )
    except Exception:
        logger.warning("os_opportunities: overdue-invoice scan failed for %s", client_id, exc_info=True)

    # Rule 3 — customer-memory write-back (propose-only): recent chats where
    # a known lead mentioned a service missing from their record.
    try:
        from backend.services import customer_memory

        writeback = customer_memory.writeback_suggestion(
            customer_memory.detect_interest_writebacks(db, client_id)
        )
        if writeback:
            suggestions.append(writeback)
    except Exception:
        logger.warning(
            "os_opportunities: memory write-back scan failed for %s",
            client_id,
            exc_info=True,
        )

    return suggestions


def _file_suggestion(db: Any, client_id: str, s: dict[str, Any]) -> bool:
    """Insert one backlog suggestion, superseding stale near-duplicates.

    Prod grew piles of same-kind cards per tenant ("3 leads went cold",
    "4 leads went cold", "6 leads went cold" — same leads, counts drifting
    week to week) because dedup matched the exact summary text. Now every
    filing first marks older pending cards of the SAME KIND ``superseded``
    so the owner always sees one card with current numbers. An identical
    pending summary still short-circuits the insert (true duplicate).
    """
    try:
        kind = _suggestion_kind(s["summary"])
        pending = (
            db.table("os_backlog_requests")
            .select("id, summary")
            .eq("client_id", client_id)
            .eq("reason", "opportunity")
            .eq("status", "pending")
            .execute()
        ).data or []
        same_kind = [
            r for r in pending if kind and _suggestion_kind(r.get("summary")) == kind
        ]
        identical = [r for r in same_kind if r.get("summary") == s["summary"]]
        stale = [r for r in same_kind if r.get("summary") != s["summary"]]

        if stale:
            db.table("os_backlog_requests").update(
                {
                    "status": "superseded",
                    "decided_by": "system",
                    "decision_note": "Superseded by a newer suggestion with current numbers",
                    "decided_at": _now(),
                }
            ).in_("id", [r["id"] for r in stale]).eq("client_id", client_id).execute()

        if identical:
            return False
        db.table("os_backlog_requests").insert(
            {
                "client_id": client_id,
                "summary": s["summary"],
                "detail": s["detail"],
                "reason": "opportunity",
                "status": "pending",
            }
        ).execute()
        return True
    except Exception:
        logger.warning("os_opportunities: filing failed for %s", client_id, exc_info=True)
        return False


async def run_opportunity_scan() -> int:
    """Nightly: file opportunity suggestions for every active paid tenant.

    Returns count of suggestions filed.
    """
    db = get_service_supabase()
    try:
        tenants = (
            db.table("tenants")
            .select("id")
            .neq("plan", "free")
            .eq("plan_status", "active")
            .limit(_TENANT_BATCH)
            .execute()
        ).data or []
    except Exception:
        logger.exception("os_opportunities: tenant query failed")
        return 0

    filed = 0
    for t in tenants:
        # At most one scan's worth of suggestions per tenant per day — the
        # automation loop ticks every 30 min; without this gate a changing
        # cold-lead count would file near-duplicate cards all day.
        try:
            recent = (
                db.table("os_backlog_requests")
                .select("id")
                .eq("client_id", t["id"])
                .eq("reason", "opportunity")
                .gte("created_at", _iso_days_ago(1))
                .limit(1)
                .execute()
            ).data
            if recent:
                continue
        except Exception:
            logger.warning("os_opportunities: daily gate read failed for %s", t["id"], exc_info=True)
            continue
        filed_here = [
            s for s in compute_suggestions(db, t["id"]) if _file_suggestion(db, t["id"], s)
        ]
        if filed_here:
            filed += len(filed_here)
            # The owner learns about new suggestions the moment they're
            # filed — cards used to land silently and rot unseen.
            await os_opportunity_notify.notify_new_suggestions(db, t["id"], filed_here)
    if filed:
        logger.info("os_opportunities: filed %d suggestions", filed)
    return filed
