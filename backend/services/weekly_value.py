"""Weekly value recap — what the AI staff was worth this week (gap G2).

One deterministic computation shared by:
  - GET /api/v1/os/insights (Agent OS recap card)
  - the Friday digest email (scheduled_jobs_ext.send_weekly_digest)

Schema notes: leads use client_id; appointments/invoices/chat_messages use tenant_id.
Every read is fault-tolerant — a partial recap beats a 500.

Dollar math
-----------
estimated_pipeline_value = sum of deal_value on new leads (per-lead values set by tenant).
When no leads have deal_value set, falls back to leads_captured * avg_lead_value
(caller-supplied default; itself defaults to 0 so the fallback is a no-op unless
the caller passes an explicit tenant setting).

This keeps the math transparent and configurable per tenant without a migration:
callers read `tenants.avg_lead_value` if the column exists and pass it here.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Default avg lead value used when a tenant has no per-lead deal_value set
# and no tenant-level override. Callers can override per tenant.
DEFAULT_AVG_LEAD_VALUE: float = 0.0


def compute_weekly_value(
    db: Any,
    client_id: str,
    avg_lead_value: float = DEFAULT_AVG_LEAD_VALUE,
) -> dict[str, Any]:
    """7-day value numbers for one tenant. Zeroes on failure, never raises.

    Parameters
    ----------
    db:             Supabase client (service role).
    client_id:      Tenant ID. Used as ``client_id`` for leads/conversations,
                    ``tenant_id`` for all other tables.
    avg_lead_value: Fallback dollar value per new lead when leads have no
                    ``deal_value`` set. Pass ``tenants.avg_lead_value`` from
                    the caller to make this configurable per tenant.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    out: dict[str, Any] = {
        "leads_captured": 0,
        "estimated_pipeline_value": 0.0,
        "appointments_booked": 0,
        "conversations_handled": 0,
        "invoices_sent": 0,
        "invoices_sent_total": 0.0,
        "invoices_paid": 0,
        "invoices_paid_total": 0.0,
        "agent_runs_completed": 0,
        "since": since,
    }

    # Leads: count + sum deal_value for estimated pipeline (client_id not tenant_id)
    try:
        leads_rows = (
            db.table("leads")
            .select("id, deal_value")
            .eq("client_id", client_id)
            .gte("created_at", since)
            .limit(500)
            .execute()
        ).data or []
        out["leads_captured"] = len(leads_rows)
        deal_value_sum = sum(float(row.get("deal_value") or 0) for row in leads_rows)
        if deal_value_sum > 0:
            out["estimated_pipeline_value"] = round(deal_value_sum, 2)
        elif out["leads_captured"] > 0 and avg_lead_value > 0:
            # Fallback: tenant-configured avg when no per-lead values exist
            out["estimated_pipeline_value"] = round(out["leads_captured"] * avg_lead_value, 2)
    except Exception:
        logger.warning("weekly_value: leads query failed for %s", client_id, exc_info=True)

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

    # Conversations handled (distinct sessions in chat_messages — tenant_id)
    try:
        msgs = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", client_id)
            .gte("created_at", since)
            .limit(5000)
            .execute()
        ).data or []
        out["conversations_handled"] = len({m["session_id"] for m in msgs if m.get("session_id")})
    except Exception:
        logger.warning(
            "weekly_value: conversations count failed for %s", client_id, exc_info=True
        )

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
