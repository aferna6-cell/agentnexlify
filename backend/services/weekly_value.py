"""Weekly value recap — what the AI staff was worth this week (gap G2).

One deterministic computation shared by:
  - GET /api/v1/os/insights (Agent OS recap card)
  - the Friday digest email (scheduled_jobs_ext.send_weekly_digest)

Schema notes: leads use client_id; appointments/invoices use tenant_id.
Every read is fault-tolerant — a partial recap beats a 500.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def compute_weekly_value(db: Any, client_id: str) -> dict[str, Any]:
    """7-day value numbers for one tenant. Zeroes on failure, never raises."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    out: dict[str, Any] = {
        "leads_captured": 0,
        "appointments_booked": 0,
        "invoices_sent": 0,
        "invoices_sent_total": 0.0,
        "invoices_paid": 0,
        "invoices_paid_total": 0.0,
        "agent_runs_completed": 0,
        "since": since,
    }

    try:
        r = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["leads_captured"] = r.count or 0
    except Exception:
        logger.warning("weekly_value: leads count failed for %s", client_id, exc_info=True)

    try:
        r = (
            db.table("appointments")
            .select("id", count="exact")
            .eq("tenant_id", client_id)
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["appointments_booked"] = r.count or 0
    except Exception:
        logger.warning("weekly_value: appointments count failed for %s", client_id, exc_info=True)

    try:
        rows = (
            db.table("invoices")
            .select("total, status, sent_at, paid_at")
            .eq("tenant_id", client_id)
            .or_(f"sent_at.gte.{since},paid_at.gte.{since}")
            .limit(500)
            .execute()
        ).data or []
        for inv in rows:
            total = float(inv.get("total") or 0)
            if (inv.get("sent_at") or "") >= since:
                out["invoices_sent"] += 1
                out["invoices_sent_total"] += total
            if (inv.get("paid_at") or "") >= since:
                out["invoices_paid"] += 1
                out["invoices_paid_total"] += total
    except Exception:
        logger.warning("weekly_value: invoices read failed for %s", client_id, exc_info=True)

    try:
        r = (
            db.table("os_agent_runs")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["agent_runs_completed"] = r.count or 0
    except Exception:
        logger.warning("weekly_value: agent runs count failed for %s", client_id, exc_info=True)

    return out
