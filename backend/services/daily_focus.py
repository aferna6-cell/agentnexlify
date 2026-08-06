"""Daily focus — "the 3 things to do today" for the dashboard.

Deterministic-first: no LLM. Four prioritized rules over data we already
have, ordered by time-sensitivity (the speed-to-lead research says minutes
matter on new leads, so those outrank everything else):

  1. New leads awaiting a first touch (status 'new')      — act in minutes
  2. Today's upcoming appointments                        — act today
  3. Warm/hot leads going quiet (7+ days, same threshold
     as the Agent OS opportunity scanner)                 — act this week
  4. Overdue invoices                                     — money on the table

Each pick carries a reason ("why this matters") so the card reads like an
assistant, not a query dump. Every rule degrades to nothing on failure —
the endpoint never 500s because one table is missing.

Schema notes: leads use client_id; appointments/invoices use tenant_id
(handled via tenant_scope helpers).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.os_opportunities import _COLD_DAYS
from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

MAX_PICKS = 3
_NAMED_LIMIT = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _named(rows: list[dict], key: str = "name") -> str:
    names = [r.get(key) or "Unnamed" for r in rows[:_NAMED_LIMIT]]
    extra = len(rows) - len(names)
    return ", ".join(names) + (f" and {extra} more" if extra > 0 else "")


def compute_daily_focus(db: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Up to MAX_PICKS focus items: {kind, title, reason, count}."""
    picks: list[dict[str, Any]] = []

    # 1 — new leads with no first touch yet (most time-sensitive)
    try:
        new_leads = (
            tenant_select(db, "leads", tenant_id, "id, name, created_at")
            .eq("status", "new")
            .order("created_at", desc=True)
            .limit(25)
            .execute()
        ).data or []
        if new_leads:
            n = len(new_leads)
            picks.append(
                {
                    "kind": "new_leads",
                    "title": f"Reply to {n} new lead{'s' if n != 1 else ''}: {_named(new_leads)}",
                    "reason": (
                        "Leads contacted within an hour are ~7x more likely to "
                        "qualify — speed wins these."
                    ),
                    "count": n,
                }
            )
    except Exception:
        logger.warning("daily_focus: new-lead rule failed for %s", tenant_id, exc_info=True)

    # 2 — today's remaining appointments
    try:
        now = _now()
        end_of_day = now.replace(hour=23, minute=59, second=59)
        appts = (
            tenant_select(db, "appointments", tenant_id, "id, customer_name, start_time")
            .eq("status", "confirmed")
            .gte("start_time", now.isoformat())
            .lte("start_time", end_of_day.isoformat())
            .order("start_time", desc=False)
            .limit(10)
            .execute()
        ).data or []
        if appts:
            n = len(appts)
            picks.append(
                {
                    "kind": "appointments_today",
                    "title": (
                        f"Prep for {n} appointment{'s' if n != 1 else ''} today: "
                        f"{_named(appts, key='customer_name')}"
                    ),
                    "reason": "Walk in prepared — open each one for a pre-meeting brief.",
                    "count": n,
                }
            )
    except Exception:
        logger.warning("daily_focus: appointment rule failed for %s", tenant_id, exc_info=True)

    # 3 — warm/hot leads going quiet (same 7-day bar as the opportunity scanner)
    try:
        cutoff = (_now() - timedelta(days=_COLD_DAYS)).isoformat()
        cold = (
            tenant_select(db, "leads", tenant_id, "id, name, updated_at")
            .in_("lead_temperature", ["warm", "hot"])
            .lt("updated_at", cutoff)
            .limit(25)
            .execute()
        ).data or []
        if cold:
            n = len(cold)
            picks.append(
                {
                    "kind": "cold_leads",
                    "title": f"Re-engage {n} lead{'s' if n != 1 else ''} going quiet: {_named(cold)}",
                    "reason": (
                        f"Warm leads untouched for {_COLD_DAYS}+ days — reach out "
                        "while there's still time."
                    ),
                    "count": n,
                }
            )
    except Exception:
        logger.warning("daily_focus: cold-lead rule failed for %s", tenant_id, exc_info=True)

    # 4 — overdue invoices
    try:
        today = _now().date().isoformat()
        overdue = (
            tenant_select(db, "invoices", tenant_id, "id, invoice_number, total, due_date")
            .eq("status", "sent")
            .lt("due_date", today)
            .limit(25)
            .execute()
        ).data or []
        if overdue:
            n = len(overdue)
            total = sum(float(i.get("total") or 0) for i in overdue)
            picks.append(
                {
                    "kind": "overdue_invoices",
                    "title": f"Chase {n} overdue invoice{'s' if n != 1 else ''} (${total:,.0f})",
                    "reason": "Money already earned — a polite reminder usually collects it.",
                    "count": n,
                }
            )
    except Exception:
        logger.warning("daily_focus: invoice rule failed for %s", tenant_id, exc_info=True)

    return picks[:MAX_PICKS]
