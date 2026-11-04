"""Daily alert when a paying tenant's widget has gone silent.

A silent widget is a paying tenant (plan other than ``free``, status
``active`` or ``trialing``) that has a ``widget_configs`` row and zero
``conversations`` in the last 7 days. ``conversations.client_id`` is the
tenant id. Demo, test, sandbox, preview, and internal tenants are skipped.

The automation loop calls this on the 30-minute cadence. The job itself
waits until 09:00 UTC and sends at most once per process per UTC day.
Nothing is emailed to the tenant. The platform owner gets one message.
"""

import html
import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.internal_tenants import is_internal_tenant
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 7
_ALERT_HOUR_UTC = 9
_PAID_STATUSES = {"active", "trialing"}
_EXCLUDED_SLUGS = {"demo", "test", "sandbox", "preview"}

_last_alert_date = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def run_quiet_client_alert(now: datetime | None = None) -> int:
    """Flag paying tenants whose widget had no conversations in 7 days.

    Returns the number of tenants included in the alert. Returns 0 before
    09:00 UTC, on a later call the same UTC day, or when nobody is silent.
    """
    global _last_alert_date

    current = now or _now_utc()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if current.hour < _ALERT_HOUR_UTC:
        return 0
    if _last_alert_date == current.date():
        return 0

    db = get_service_supabase()
    since = (current - timedelta(days=_WINDOW_DAYS)).isoformat()

    try:
        widget_rows = (
            db.table("widget_configs").select("tenant_id").execute()
        ).data or []
    except Exception:
        logger.warning("quiet_client_alert: widget_configs query failed")
        return 0

    tenant_ids = []
    seen = set()
    for row in widget_rows:
        tenant_id = row.get("tenant_id")
        if tenant_id and tenant_id not in seen:
            seen.add(tenant_id)
            tenant_ids.append(tenant_id)
    if not tenant_ids:
        _last_alert_date = current.date()
        return 0

    try:
        tenant_rows = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status, business_slug")
            .in_("id", tenant_ids)
            .execute()
        ).data or []
    except Exception:
        logger.warning("quiet_client_alert: tenants query failed")
        return 0

    silent = []
    for row in tenant_rows:
        tenant_id = row.get("id") or ""
        plan = str(row.get("plan") or "free").lower()
        plan_status = str(row.get("plan_status") or "").lower()
        slug = str(row.get("business_slug") or "").strip().lower()
        if not tenant_id or plan == "free" or plan_status not in _PAID_STATUSES:
            continue
        if slug in _EXCLUDED_SLUGS or is_internal_tenant(row):
            continue
        try:
            recent = (
                db.table("conversations")
                .select("id")
                .eq("client_id", tenant_id)
                .gte("created_at", since)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning(
                "quiet_client_alert: conversations query failed tenant=%s",
                tenant_id,
            )
            continue
        if recent.data:
            continue
        silent.append(
            {
                "tenant_id": tenant_id,
                "business_name": row.get("business_name") or tenant_id,
                "plan": plan,
            }
        )

    _last_alert_date = current.date()
    if not silent:
        logger.info("quiet_client_alert: no silent paying widgets")
        return 0

    logger.warning(
        "quiet_client_alert: %d paying widget tenant(s) silent for %d days: %s",
        len(silent),
        _WINDOW_DAYS,
        ",".join(item["tenant_id"] for item in silent),
    )
    try:
        await _send_alert(silent)
    except Exception:
        logger.warning("quiet_client_alert: platform email failed")
    return len(silent)


async def _send_alert(silent: list[dict]) -> None:
    items = "".join(
        "<li>{name} — {plan} — {tenant_id}</li>".format(
            name=html.escape(str(item["business_name"])),
            plan=html.escape(str(item["plan"])),
            tenant_id=html.escape(str(item["tenant_id"])),
        )
        for item in silent
    )
    await send_platform_email(
        subject=(
            f"Quiet widget: {len(silent)} paying tenant(s) "
            f"silent for {_WINDOW_DAYS} days"
        ),
        body_html=(
            f"<p>{len(silent)} paying tenant(s) with a widget had zero "
            f"conversations in the last {_WINDOW_DAYS} days.</p>"
            f"<ul>{items}</ul>"
            "<p>This is an internal flag. Nothing was sent to the tenant.</p>"
        ),
    )
