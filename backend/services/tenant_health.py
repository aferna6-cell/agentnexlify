"""Per-tenant activation and health metrics for the admin convert/retain motion.

Computes, for every tenant row, counts of chat_messages, leads, and appointments
plus a 7-day and 30-day activity window, then derives a tri-state status:
  active  — activity in the last 7 days
  at_risk — activity in the last 8–30 days (not 7)
  dormant — no activity in the last 30 days

Schema conventions (see schema-discipline.md):
  leads         → client_id   (NOT tenant_id)
  chat_messages → tenant_id
  appointments  → tenant_id
  tenants       → id (primary key, used as tenant_id elsewhere)

Paid definition: plan != 'free' AND plan_status IN ('active', 'trialing').

Internal-tenant exclusion:
  Tenants whose business_name matches known internal/test patterns
  (see backend/services/internal_tenants.py) are excluded from the
  health report so the per-tenant view only shows real customers.

Row caps on full-table scans:
  chat_messages, leads, and appointments are capped at 50 000 rows each
  to prevent unbounded memory usage on large installations.  If a platform
  grows past that threshold the per-tenant counts will be approximate,
  but the health-status classification (active/at_risk/dormant) will
  still be correct for the vast majority of tenants.

Each per-tenant metric block uses its own try/except so a single tenant DB failure
does not abort the whole report (mirrors funnel_metrics.py style).
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.internal_tenants import is_internal_tenant

logger = logging.getLogger(__name__)

_PAID_PLANS = {"chatbot", "agent_os", "agent_os_managed", "growth", "autopilot", "professional", "enterprise"}
_PAID_STATUSES = {"active", "trialing"}

# Thresholds for status classification
_ACTIVE_DAYS = 7
_AT_RISK_DAYS = 30

# Row cap for full-table scans on activity tables.
# Prevents unbounded memory on large installations.
_ROW_CAP = 50_000


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _status_from_last_activity(last_activity_at: str | None) -> str:
    """Derive tri-state status from last_activity_at ISO string.

    active  — activity within last 7 days
    at_risk — activity within last 8-30 days
    dormant — no activity OR last activity >30 days ago
    """
    if not last_activity_at:
        return "dormant"
    try:
        ts = datetime.fromisoformat(last_activity_at.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = _now_utc()
        delta = now - ts
        if delta.days <= _ACTIVE_DAYS:
            return "active"
        if delta.days <= _AT_RISK_DAYS:
            return "at_risk"
        return "dormant"
    except Exception:
        logger.warning("tenant_health: could not parse last_activity_at %r", last_activity_at)
        return "dormant"


def _is_paid(plan: str | None, plan_status: str | None) -> bool:
    return (
        plan is not None
        and plan != "free"
        and plan in _PAID_PLANS
        and plan_status in _PAID_STATUSES
    )


def compute_tenant_health() -> dict:
    """Return per-tenant health report.  Never raises — errors degrade to empty tenants list.

    Internal/test tenants (see backend/services/internal_tenants.py) are
    excluded so the report only reflects real customer activity.

    Returns
    -------
    dict with keys:
        tenants     list  — one entry per real customer tenant
        computed_at str   — UTC ISO timestamp
    """
    db = get_service_supabase()
    now = _now_utc()
    since_7d = _iso(now - timedelta(days=_ACTIVE_DAYS))
    since_30d = _iso(now - timedelta(days=_AT_RISK_DAYS))

    tenants: list[dict] = []

    # --- 1. Fetch all tenants, excluding internal/test accounts ---
    try:
        resp = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status")
            .execute()
        )
        tenant_rows = [
            row for row in (resp.data or [])
            if not is_internal_tenant(row)
        ]
    except Exception:
        logger.exception("tenant_health: failed to fetch tenants table")
        return {
            "tenants": [],
            "computed_at": _iso(now),
        }

    # --- 2. Fetch aggregate counts across all tenants (bulk fetch, deduplicate in Python) ---
    # Capped at _ROW_CAP rows per table to bound memory usage at scale.

    # chat_messages totals per tenant_id
    all_messages: dict[str, int] = {}
    all_messages_7d: dict[str, int] = {}
    all_messages_last: dict[str, str] = {}
    try:
        resp = (
            db.table("chat_messages")
            .select("tenant_id, created_at")
            .limit(_ROW_CAP)
            .execute()
        )
        for row in resp.data or []:
            tid = row.get("tenant_id")
            cat = row.get("created_at", "")
            if not tid:
                continue
            all_messages[tid] = all_messages.get(tid, 0) + 1
            # Track most recent
            if cat > all_messages_last.get(tid, ""):
                all_messages_last[tid] = cat
            if cat >= since_7d:
                all_messages_7d[tid] = all_messages_7d.get(tid, 0) + 1
    except Exception:
        logger.exception("tenant_health: failed to fetch chat_messages")

    # leads totals per client_id (leads use client_id, not tenant_id)
    all_leads: dict[str, int] = {}
    all_leads_7d: dict[str, int] = {}
    all_leads_last: dict[str, str] = {}
    try:
        resp = (
            db.table("leads")
            .select("client_id, created_at")
            .limit(_ROW_CAP)
            .execute()
        )
        for row in resp.data or []:
            cid = row.get("client_id")
            cat = row.get("created_at", "")
            if not cid:
                continue
            all_leads[cid] = all_leads.get(cid, 0) + 1
            if cat > all_leads_last.get(cid, ""):
                all_leads_last[cid] = cat
            if cat >= since_7d:
                all_leads_7d[cid] = all_leads_7d.get(cid, 0) + 1
    except Exception:
        logger.exception("tenant_health: failed to fetch leads")

    # appointments totals per tenant_id
    all_appts: dict[str, int] = {}
    all_appts_last: dict[str, str] = {}
    try:
        resp = (
            db.table("appointments")
            .select("tenant_id, created_at")
            .limit(_ROW_CAP)
            .execute()
        )
        for row in resp.data or []:
            tid = row.get("tenant_id")
            cat = row.get("created_at", "")
            if not tid:
                continue
            all_appts[tid] = all_appts.get(tid, 0) + 1
            if cat > all_appts_last.get(tid, ""):
                all_appts_last[tid] = cat
    except Exception:
        logger.exception("tenant_health: failed to fetch appointments")

    # --- 3. Build per-tenant entries ---
    for row in tenant_rows:
        try:
            tid = row.get("id") or row.get("tenant_id") or ""
            if not tid:
                continue

            plan = row.get("plan") or "free"
            plan_status = row.get("plan_status") or ""
            business_name = row.get("business_name") or ""

            total_messages = all_messages.get(tid, 0)
            total_leads = all_leads.get(tid, 0)
            total_appointments = all_appts.get(tid, 0)
            messages_last_7d = all_messages_7d.get(tid, 0)
            leads_last_7d = all_leads_7d.get(tid, 0)

            # last_activity_at = latest created_at across all three sources
            candidates = [
                all_messages_last.get(tid, ""),
                all_leads_last.get(tid, ""),
                all_appts_last.get(tid, ""),
            ]
            last_activity_at: str | None = max(candidates) or None

            status = _status_from_last_activity(last_activity_at)

            tenants.append(
                {
                    "tenant_id": tid,
                    "business_name": business_name,
                    "plan": plan,
                    "plan_status": plan_status,
                    "is_paid": _is_paid(plan, plan_status),
                    "total_messages": total_messages,
                    "total_leads": total_leads,
                    "total_appointments": total_appointments,
                    "messages_last_7d": messages_last_7d,
                    "leads_last_7d": leads_last_7d,
                    "last_activity_at": last_activity_at,
                    "status": status,
                }
            )
        except Exception:
            logger.exception("tenant_health: failed to build entry for tenant %r", row.get("id"))

    return {
        "tenants": tenants,
        "computed_at": _iso(now),
    }
