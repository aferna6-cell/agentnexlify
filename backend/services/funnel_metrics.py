"""Platform funnel metrics — signup → activation → lead → paid.

Each metric is computed independently so a DB failure on one counter does
not prevent the others from returning.  Partial failure is surfaced via the
``errors`` key in the response so callers can detect degraded data.

Schema conventions enforced here (see schema-discipline.md):
- leads        → ``client_id`` (NOT tenant_id)
- chat_messages → ``tenant_id``
- appointments  → ``tenant_id``
- tenants       → ``tenant_id`` == ``id`` (primary key)
- conversations → ``client_id`` (NOT tenant_id)

Paid definition: plan != 'free' AND plan_status IN ('active', 'trialing').
Activated definition: tenant has >=1 chat_message OR widget_configs row with
  a non-null, non-empty business_name (i.e. completed setup). We query
  chat_messages as the primary proxy because that table is always present and
  a message means the widget was actually used.

This-week window: calendar week (Mon 00:00 UTC to now).
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Plans that are considered paid (not free/lapsed)
_PAID_PLANS = {"chatbot", "agent_os", "growth", "autopilot", "professional", "enterprise"}
_PAID_STATUSES = {"active", "trialing"}


def _week_start() -> str:
    """ISO timestamp for Monday 00:00 UTC of the current week."""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return monday.isoformat()


def compute_funnel() -> dict:
    """Return platform funnel counts. Best-effort — never raises.

    Returns
    -------
    dict with keys:
        total_tenants       int   — all rows in tenants table
        activated           int   — tenants with >=1 chat_message
        with_leads          int   — tenants that have >=1 lead
        paid                int   — tenants on a paid plan with active/trialing status
        new_signups_week    int   — tenants created this calendar week (Mon–now)
        new_leads_week      int   — leads created this calendar week
        new_appointments_week int — appointments created this calendar week
        errors              list  — names of metrics that failed (DB error)
        computed_at         str   — UTC ISO timestamp
    """
    db = get_service_supabase()
    since = _week_start()
    errors: list[str] = []

    result: dict = {
        "total_tenants": 0,
        "activated": 0,
        "with_leads": 0,
        "paid": 0,
        "new_signups_week": 0,
        "new_leads_week": 0,
        "new_appointments_week": 0,
        "errors": errors,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Total tenants
    try:
        resp = db.table("tenants").select("id", count="exact").execute()
        result["total_tenants"] = resp.count or 0
    except Exception:
        logger.exception("funnel_metrics: failed to count total_tenants")
        errors.append("total_tenants")

    # 2. Activated — tenants with >=1 chat_message (widget actually used)
    # We count distinct tenant_id values by fetching tenant_ids and deduping.
    # Supabase Python client does not expose SELECT DISTINCT natively, so we
    # use a count=exact on a group-by workaround: select tenant_id, limit high,
    # then deduplicate in Python. Capped at 5000 rows to keep latency bounded.
    try:
        resp = (
            db.table("chat_messages")
            .select("tenant_id")
            .limit(5000)
            .execute()
        )
        distinct_activated = {row["tenant_id"] for row in (resp.data or []) if row.get("tenant_id")}
        result["activated"] = len(distinct_activated)
    except Exception:
        logger.exception("funnel_metrics: failed to count activated")
        errors.append("activated")

    # 3. Tenants with >=1 lead (leads use client_id)
    try:
        resp = (
            db.table("leads")
            .select("client_id")
            .limit(5000)
            .execute()
        )
        distinct_with_leads = {row["client_id"] for row in (resp.data or []) if row.get("client_id")}
        result["with_leads"] = len(distinct_with_leads)
    except Exception:
        logger.exception("funnel_metrics: failed to count with_leads")
        errors.append("with_leads")

    # 4. Paid tenants — plan not 'free' AND plan_status in active/trialing
    try:
        resp = (
            db.table("tenants")
            .select("id", count="exact")
            .neq("plan", "free")
            .in_("plan_status", list(_PAID_STATUSES))
            .execute()
        )
        result["paid"] = resp.count or 0
    except Exception:
        logger.exception("funnel_metrics: failed to count paid")
        errors.append("paid")

    # 5. New signups this week
    try:
        resp = (
            db.table("tenants")
            .select("id", count="exact")
            .gte("created_at", since)
            .execute()
        )
        result["new_signups_week"] = resp.count or 0
    except Exception:
        logger.exception("funnel_metrics: failed to count new_signups_week")
        errors.append("new_signups_week")

    # 6. New leads this week (leads use client_id; created_at is standard)
    try:
        resp = (
            db.table("leads")
            .select("id", count="exact")
            .gte("created_at", since)
            .execute()
        )
        result["new_leads_week"] = resp.count or 0
    except Exception:
        logger.exception("funnel_metrics: failed to count new_leads_week")
        errors.append("new_leads_week")

    # 7. New appointments this week (appointments use tenant_id)
    try:
        resp = (
            db.table("appointments")
            .select("id", count="exact")
            .gte("created_at", since)
            .execute()
        )
        result["new_appointments_week"] = resp.count or 0
    except Exception:
        logger.exception("funnel_metrics: failed to count new_appointments_week")
        errors.append("new_appointments_week")

    return result
