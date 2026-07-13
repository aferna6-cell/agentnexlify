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

Internal-tenant exclusion:
  Tenants whose business_name matches known internal/test patterns
  (see backend/services/internal_tenants.py) are excluded from ALL
  metrics so counts reflect real customers only.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.internal_tenants import is_internal_tenant

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

    Internal/test tenants are excluded from all counts.  This prevents
    the "AgentNexLiFy Smoke Test" tenant (which holds ~49% of all
    chat_messages as of 2026-06-23) from inflating every metric.

    Returns
    -------
    dict with keys:
        total_tenants       int   — real customers in tenants table
        activated           int   — real tenants with >=1 chat_message
        with_leads          int   — real tenants that have >=1 lead
        paid                int   — real tenants on a paid plan with active/trialing status
        new_signups_week    int   — real tenants created this calendar week (Mon–now)
        new_leads_week      int   — leads from real tenants created this calendar week
        new_appointments_week int — appointments from real tenants this calendar week
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
        "with_appointments": 0,
        "paid": 0,
        "retained_30d": 0,
        "new_signups_week": 0,
        "new_leads_week": 0,
        "new_appointments_week": 0,
        "errors": errors,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- Step 0: Fetch all tenants and build real-tenant ID set ---
    # We fetch once and use it for all tenant-scoped metrics.  Internal
    # tenants are filtered out here so every metric below only counts
    # real customers.
    real_tenant_ids: set[str] = set()
    real_tenant_rows: list[dict] = []
    try:
        resp = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status, created_at")
            .execute()
        )
        for row in resp.data or []:
            if not is_internal_tenant(row):
                real_tenant_rows.append(row)
                tid = row.get("id") or ""
                if tid:
                    real_tenant_ids.add(tid)
    except Exception:
        logger.exception("funnel_metrics: failed to fetch tenants table")
        errors.append("total_tenants")
        errors.append("paid")
        errors.append("new_signups_week")
        # Continue so the other three metrics (activated, with_leads, appts)
        # can still be attempted.  Without real_tenant_ids they will return 0.

    # 1. Total tenants — count of real customers
    if "total_tenants" not in errors:
        result["total_tenants"] = len(real_tenant_rows)

    # 4. Paid tenants — plan not 'free' AND plan_status in active/trialing
    if "paid" not in errors:
        result["paid"] = sum(
            1
            for row in real_tenant_rows
            if (
                row.get("plan") not in (None, "free")
                and row.get("plan") in _PAID_PLANS
                and row.get("plan_status") in _PAID_STATUSES
            )
        )

    # 4b. Retained — paid tenants that signed up 30+ days ago and are still
    # paying (plan_status active). The GTM funnel is signup -> activate ->
    # first-lead -> paid -> RETAINED; this is the deterministic stand-in until
    # per-tenant churn events exist.
    if "paid" not in errors:
        retained_cutoff = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        result["retained_30d"] = sum(
            1
            for row in real_tenant_rows
            if (
                row.get("plan") not in (None, "free")
                and row.get("plan") in _PAID_PLANS
                and row.get("plan_status") in _PAID_STATUSES
                and (row.get("created_at") or "") <= retained_cutoff
            )
        )

    # 5. New signups this week
    if "new_signups_week" not in errors:
        result["new_signups_week"] = sum(
            1
            for row in real_tenant_rows
            if (row.get("created_at") or "") >= since
        )

    # 2. Activated — real tenants with >=1 chat_message (widget actually used)
    # Supabase Python client does not expose SELECT DISTINCT natively, so we
    # fetch tenant_id values and deduplicate in Python.  Capped at 50000 rows
    # to keep latency bounded on large installations.
    try:
        resp = (
            db.table("chat_messages")
            .select("tenant_id")
            .limit(50000)
            .execute()
        )
        distinct_activated = {
            row["tenant_id"]
            for row in (resp.data or [])
            if row.get("tenant_id") and row["tenant_id"] in real_tenant_ids
        }
        result["activated"] = len(distinct_activated)
    except Exception:
        logger.exception("funnel_metrics: failed to count activated")
        errors.append("activated")

    # 3. Tenants with >=1 lead (leads use client_id)
    try:
        resp = (
            db.table("leads")
            .select("client_id")
            .limit(50000)
            .execute()
        )
        distinct_with_leads = {
            row["client_id"]
            for row in (resp.data or [])
            if row.get("client_id") and row["client_id"] in real_tenant_ids
        }
        result["with_leads"] = len(distinct_with_leads)
    except Exception:
        logger.exception("funnel_metrics: failed to count with_leads")
        errors.append("with_leads")

    # 3b. Tenants with >=1 appointment (appointments use tenant_id). Bookings
    # are the funnel stage under active watch (GH #412 re-measure) - a weekly
    # delta alone can't show whether ANY tenant has ever converted a booking.
    try:
        resp = (
            db.table("appointments")
            .select("tenant_id")
            .limit(50000)
            .execute()
        )
        distinct_with_appts = {
            row["tenant_id"]
            for row in (resp.data or [])
            if row.get("tenant_id") and row["tenant_id"] in real_tenant_ids
        }
        result["with_appointments"] = len(distinct_with_appts)
    except Exception:
        logger.exception("funnel_metrics: failed to count with_appointments")
        errors.append("with_appointments")

    # 6. New leads this week (leads use client_id; created_at is standard)
    # Fetch rows for the week and filter by real tenant IDs in Python.
    try:
        resp = (
            db.table("leads")
            .select("client_id, created_at")
            .gte("created_at", since)
            .limit(50000)
            .execute()
        )
        result["new_leads_week"] = sum(
            1
            for row in (resp.data or [])
            if row.get("client_id") and row["client_id"] in real_tenant_ids
        )
    except Exception:
        logger.exception("funnel_metrics: failed to count new_leads_week")
        errors.append("new_leads_week")

    # 7. New appointments this week (appointments use tenant_id)
    try:
        resp = (
            db.table("appointments")
            .select("tenant_id, created_at")
            .gte("created_at", since)
            .limit(50000)
            .execute()
        )
        result["new_appointments_week"] = sum(
            1
            for row in (resp.data or [])
            if row.get("tenant_id") and row["tenant_id"] in real_tenant_ids
        )
    except Exception:
        logger.exception("funnel_metrics: failed to count new_appointments_week")
        errors.append("new_appointments_week")

    return result
