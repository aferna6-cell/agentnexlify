"""Weekly churn-watch job — alerts the platform owner about at-risk paid tenants.

At-risk definition: paid tenant (plan != 'free' AND plan_status IN ('active','trialing'))
with ZERO leads AND ZERO chat_messages in the last 14 days.

Schema conventions (schema-discipline.md):
  leads         → client_id   (NOT tenant_id)
  chat_messages → tenant_id
  tenants       → id

Runs in the 30-min automation loop on Sundays (weekday() == 6) to give the
owner a start-of-week view. If no tenants are at risk, sends nothing.

Never raises — every error is caught and logged.
"""

import html
import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 14
_PAID_STATUSES = ("active", "trialing")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def run_churn_watch() -> int:
    """Identify at-risk paid tenants and email the owner if any exist.

    A tenant is at-risk when it has ZERO leads captured AND ZERO chat_messages
    in the last 14 days.

    Returns
    -------
    int
        Number of at-risk tenants included in the alert (0 if none or if error).
    """
    db = get_service_supabase()
    now = _now_utc()

    # Only run on Sundays (weekday() == 6) — gives owner a start-of-week view.
    if now.weekday() != 6:
        return 0

    since = (now - timedelta(days=_WINDOW_DAYS)).isoformat()

    # --- Fetch paid tenants ---
    try:
        resp = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status")
            .neq("plan", "free")
            .in_("plan_status", list(_PAID_STATUSES))
            .execute()
        )
        tenant_rows = resp.data or []
    except Exception:
        logger.exception("churn_watch: failed to fetch paid tenants")
        return 0

    if not tenant_rows:
        return 0

    at_risk: list[dict] = []

    for row in tenant_rows:
        tid = row.get("id", "")
        if not tid:
            continue

        plan = row.get("plan") or "free"
        plan_status = row.get("plan_status") or ""

        # Python-level guard (DB filters may not apply in unit-test mocks)
        if plan == "free" or plan_status not in _PAID_STATUSES:
            continue

        business_name = row.get("business_name") or tid

        try:
            # Check leads in last 14 days (leads use client_id, not tenant_id)
            leads_resp = (
                db.table("leads")
                .select("id")
                .eq("client_id", tid)
                .gte("created_at", since)
                .limit(1)
                .execute()
            )
            recent_leads = len(leads_resp.data or [])
        except Exception:
            logger.warning(
                "churn_watch: leads query failed for tenant %s — skipping", tid, exc_info=True
            )
            continue

        try:
            # Check chat_messages in last 14 days (chat_messages use tenant_id)
            msgs_resp = (
                db.table("chat_messages")
                .select("id")
                .eq("tenant_id", tid)
                .gte("created_at", since)
                .limit(1)
                .execute()
            )
            recent_messages = len(msgs_resp.data or [])
        except Exception:
            logger.warning(
                "churn_watch: chat_messages query failed for tenant %s — skipping",
                tid,
                exc_info=True,
            )
            continue

        if recent_leads == 0 and recent_messages == 0:
            at_risk.append(
                {
                    "tenant_id": tid,
                    "business_name": business_name,
                    "plan": plan,
                    "plan_status": plan_status,
                }
            )

    if not at_risk:
        return 0

    # --- Build and send alert email ---
    try:
        await _send_churn_alert(at_risk=at_risk, window_days=_WINDOW_DAYS)
    except Exception:
        logger.exception("churn_watch: failed to send alert email")

    return len(at_risk)


async def _send_churn_alert(*, at_risk: list[dict], window_days: int) -> None:
    """Build and send the owner alert listing at-risk tenants."""
    count = len(at_risk)
    subject = f"Churn Watch: {count} paid tenant{'s' if count != 1 else ''} with no activity in {window_days}d"

    rows_html = ""
    for t in at_risk:
        name = html.escape(t.get("business_name") or t.get("tenant_id", "Unknown"))
        plan = html.escape(t.get("plan") or "")
        status = html.escape(t.get("plan_status") or "")
        tid = html.escape(t.get("tenant_id") or "")
        rows_html += (
            "<tr>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{name}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{plan}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{status}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;font-family:monospace;font-size:12px;'>{tid}</td>"
            "</tr>"
        )

    body_html = (
        "<div style='font-family:sans-serif;max-width:700px;margin:0 auto;'>"
        "<h2 style='color:#dc2626;'>Churn Watch Alert</h2>"
        f"<p style='color:#374151;'>"
        f"<strong>{count}</strong> paid tenant{'s have' if count != 1 else ' has'} "
        f"had <strong>zero leads and zero chat messages in the last {window_days} days</strong>. "
        f"These customers may be churning silently.</p>"
        "<table style='border-collapse:collapse;width:100%;margin:16px 0;'>"
        "<thead>"
        "<tr style='background:#f3f4f6;'>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Business</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Plan</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Status</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Tenant ID</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "<p style='color:#6b7280;margin-top:16px;'>Review at "
        "<a href='https://app.agentnexlify.com' style='color:#3b82f6;'>app.agentnexlify.com</a>"
        " — consider reaching out to re-engage before they cancel.</p>"
        "</div>"
    )

    await send_platform_email(subject=subject, body_html=body_html)
    logger.info("churn_watch: alert sent for %d at-risk tenants", count)
