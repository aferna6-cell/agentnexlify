"""Admin tenant health board — per-tenant red/yellow/green for partner account management.

All endpoints are protected by the API secret key (internal admin only, not tenant-facing).
Tables:
    tenants       (id, business_name, plan, created_at, is_demo)
    leads         (client_id, created_at) — leads uses client_id, NOT tenant_id
    os_agent_runs (client_id, deliverable_status, created_at) — also client_id

Health rules:
    red    — no leads ever AND tenant is 7+ days old, OR any draft rotting
             (deliverable_status='pending_approval' older than 48h)
    yellow — no leads in last 7 days, OR pending drafts > 3
    green  — otherwise
"""

import logging
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])

_RECENT_LEAD_DAYS = 7
_TENANT_GRACE_DAYS = 7
_DRAFT_ROT_HOURS = 48
_PENDING_DRAFTS_YELLOW_THRESHOLD = 3

_HEALTH_ORDER = {"red": 0, "yellow": 1, "green": 2}


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    """Verify caller has the platform admin secret. Raises 401 on failure."""
    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _parse_ts(value) -> datetime | None:
    """Parse a Supabase ISO timestamp into an aware UTC datetime. None on failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


@router.get("/tenant-health")
@limiter.limit("10/minute")
async def get_tenant_health(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Every tenant as a row with red/yellow/green health, sorted red first.

    Returns a list of:
        {tenant_id, business_name, plan, created_at, is_demo,
         leads_7d, leads_total, pending_drafts, drafts_rotting,
         last_lead_at, health}

    Demo tenants are included and flagged via is_demo — nothing is excluded.
    """
    _verify_admin_secret(x_api_secret)

    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=_RECENT_LEAD_DAYS)
    rot_cutoff = now - timedelta(hours=_DRAFT_ROT_HOURS)

    try:
        db = get_service_supabase()

        tenants_result = (
            db.table("tenants")
            .select("id, business_name, plan, created_at, is_demo")
            .execute()
        )

        # One select of two light columns, aggregated in Python — leads_total is
        # all-time and last_lead_at needs the max timestamp, so a time-windowed
        # query can't produce them. Zero per-tenant queries; fine at current scale.
        leads_result = db.table("leads").select("client_id, created_at").execute()

        drafts_result = (
            db.table("os_agent_runs")
            .select("client_id, created_at")
            .eq("deliverable_status", "pending_approval")
            .execute()
        )
    except Exception:
        logger.exception("Failed to query tenant health data")
        raise HTTPException(status_code=500, detail="Failed to load tenant health data")

    # Aggregate leads per client_id.
    leads_total: dict[str, int] = {}
    leads_7d: dict[str, int] = {}
    last_lead_at: dict[str, datetime] = {}
    for row in leads_result.data or []:
        client_id = row.get("client_id")
        if not client_id:
            continue
        leads_total[client_id] = leads_total.get(client_id, 0) + 1
        ts = _parse_ts(row.get("created_at"))
        if ts is None:
            continue
        if ts >= recent_cutoff:
            leads_7d[client_id] = leads_7d.get(client_id, 0) + 1
        previous = last_lead_at.get(client_id)
        if previous is None or ts > previous:
            last_lead_at[client_id] = ts

    # Aggregate pending drafts per client_id.
    pending_drafts: dict[str, int] = {}
    drafts_rotting: dict[str, int] = {}
    for row in drafts_result.data or []:
        client_id = row.get("client_id")
        if not client_id:
            continue
        pending_drafts[client_id] = pending_drafts.get(client_id, 0) + 1
        ts = _parse_ts(row.get("created_at"))
        if ts is not None and ts < rot_cutoff:
            drafts_rotting[client_id] = drafts_rotting.get(client_id, 0) + 1

    rows = []
    for tenant in tenants_result.data or []:
        tenant_id = tenant.get("id")
        if not tenant_id:
            continue

        total = leads_total.get(tenant_id, 0)
        recent = leads_7d.get(tenant_id, 0)
        pending = pending_drafts.get(tenant_id, 0)
        rotting = drafts_rotting.get(tenant_id, 0)

        created = _parse_ts(tenant.get("created_at"))
        age_days = (now - created).days if created else 0

        if (total == 0 and age_days >= _TENANT_GRACE_DAYS) or rotting > 0:
            health = "red"
        elif recent == 0 or pending > _PENDING_DRAFTS_YELLOW_THRESHOLD:
            health = "yellow"
        else:
            health = "green"

        last_lead = last_lead_at.get(tenant_id)
        rows.append(
            {
                "tenant_id": tenant_id,
                "business_name": tenant.get("business_name"),
                "plan": tenant.get("plan"),
                "created_at": tenant.get("created_at"),
                "is_demo": bool(tenant.get("is_demo")),
                "leads_7d": recent,
                "leads_total": total,
                "pending_drafts": pending,
                "drafts_rotting": rotting,
                "last_lead_at": last_lead.isoformat() if last_lead else None,
                "health": health,
            }
        )

    rows.sort(
        key=lambda r: (
            _HEALTH_ORDER[r["health"]],
            (r["business_name"] or "").lower(),
        )
    )
    return rows
