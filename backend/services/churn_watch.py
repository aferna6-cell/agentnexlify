"""Weekly churn-watch job — alerts the platform owner about at-risk paid tenants.

At-risk definition: paid tenant (plan != 'free' AND plan_status IN ('active','trialing'))
with ZERO leads AND ZERO chat_messages in the last 14 days.

The alert is a CALL LIST, not just a table: each at-risk tenant row carries
its last recorded activity date and a ready-to-send re-engagement email draft
the owner can copy, personalize, and send. Drafts are suggestions only —
nothing is sent to the tenant automatically (drafts-only trust boundary).

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
from backend.services.internal_tenants import is_internal_tenant
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 14
_PAID_STATUSES = ("active", "trialing")

# Monthly price by current purchasable plan — frames what silent churn costs.
# Legacy/grandfathered plans (growth, autopilot, professional, enterprise)
# have per-contract pricing and are shown without a dollar figure.
_PLAN_MRR: dict[str, str] = {
    "chatbot": "$19.99/mo",
    "agent_os": "$99.99/mo",
    "agent_os_managed": "$299.99/mo",
}


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
            .select("id, business_name, plan, plan_status, owner_email")
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

    # Exclude internal/test tenants — they should never trigger a churn alert.
    # See backend/services/internal_tenants.py for the denylist.
    tenant_rows = [row for row in tenant_rows if not is_internal_tenant(row)]
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
                    "owner_email": row.get("owner_email") or "",
                    "last_activity": _last_activity(db, tid),
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


def _last_activity(db, tenant_id: str) -> str:
    """Most recent lead or chat_message timestamp for a tenant, '' if none.

    Only called for at-risk tenants (a handful of rows), so the two extra
    queries per tenant are cheap. Best-effort — returns '' on any failure.
    """
    latest = ""
    try:
        resp = (
            db.table("leads")
            .select("created_at")
            .eq("client_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            latest = resp.data[0].get("created_at") or ""
    except Exception:
        logger.warning(
            "churn_watch: last-lead lookup failed for %s", tenant_id, exc_info=True
        )
    try:
        resp = (
            db.table("chat_messages")
            .select("created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            candidate = resp.data[0].get("created_at") or ""
            if candidate > latest:
                latest = candidate
    except Exception:
        logger.warning(
            "churn_watch: last-message lookup failed for %s", tenant_id, exc_info=True
        )
    return latest


def _reengagement_draft(tenant: dict, window_days: int) -> str:
    """Plain-text re-engagement email the owner can copy, edit, and send.

    A draft only — churn_watch never emails the tenant directly
    (drafts-only trust boundary, see module docstring).
    """
    name = (tenant.get("business_name") or "there").strip()
    return (
        f"Subject: Getting more out of your AI assistant at {name}\n"
        "\n"
        f"Hi {name} team,\n"
        "\n"
        f"I noticed your AI assistant hasn't had any visitor conversations in the "
        f"last {window_days} days. Usually that means the widget isn't on the pages "
        "your visitors land on, or your site traffic dipped.\n"
        "\n"
        "I'd like to fix that with you this week. In 10 minutes we can:\n"
        "- confirm the widget is live on your busiest pages\n"
        "- tune the greeting so more visitors start a conversation\n"
        "- switch on appointment booking so leads can book you directly\n"
        "\n"
        "Reply to this email and I'll make it happen.\n"
        "\n"
        "[Your name]\n"
        "AgentNexLiFy"
    )


def _format_last_activity(value: str) -> str:
    if not value:
        return "No activity recorded"
    return value[:10]  # ISO date part


async def _send_churn_alert(*, at_risk: list[dict], window_days: int) -> None:
    """Build and send the owner call list for at-risk tenants."""
    count = len(at_risk)
    subject = f"Churn Watch: {count} paid tenant{'s' if count != 1 else ''} with no activity in {window_days}d"

    rows_html = ""
    for t in at_risk:
        name = html.escape(t.get("business_name") or t.get("tenant_id", "Unknown"))
        plan = html.escape(t.get("plan") or "")
        mrr = html.escape(_PLAN_MRR.get(t.get("plan") or "", ""))
        plan_label = f"{plan} ({mrr})" if mrr else plan
        status = html.escape(t.get("plan_status") or "")
        owner_email = html.escape(t.get("owner_email") or "")
        last_seen = html.escape(_format_last_activity(t.get("last_activity") or ""))
        rows_html += (
            "<tr>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{name}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{plan_label}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{status}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;'>{last_seen}</td>"
            f"<td style='padding:8px 12px;border:1px solid #e5e7eb;font-family:monospace;font-size:12px;'>{owner_email}</td>"
            "</tr>"
        )

    # One copy-paste draft per at-risk tenant, under the table.
    drafts_html = ""
    for t in at_risk:
        name = html.escape(t.get("business_name") or t.get("tenant_id", "Unknown"))
        mailto = html.escape(t.get("owner_email") or "")
        draft = html.escape(_reengagement_draft(t, window_days))
        mailto_line = (
            f"<p style='color:#374151;margin:4px 0;'>Send to: "
            f"<a href='mailto:{mailto}' style='color:#3b82f6;'>{mailto}</a></p>"
            if mailto
            else ""
        )
        drafts_html += (
            f"<h3 style='color:#111827;margin:20px 0 4px;'>Draft for {name}</h3>"
            f"{mailto_line}"
            "<pre style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;"
            "padding:12px;font-size:13px;white-space:pre-wrap;color:#111827;'>"
            f"{draft}</pre>"
        )

    body_html = (
        "<div style='font-family:sans-serif;max-width:700px;margin:0 auto;'>"
        "<h2 style='color:#dc2626;'>Churn Watch — this week's call list</h2>"
        f"<p style='color:#374151;'>"
        f"<strong>{count}</strong> paid tenant{'s have' if count != 1 else ' has'} "
        f"had <strong>zero leads and zero chat messages in the last {window_days} days</strong>. "
        f"These customers may be churning silently — one personal email each is the "
        f"highest-ROI 30 minutes this week.</p>"
        "<table style='border-collapse:collapse;width:100%;margin:16px 0;'>"
        "<thead>"
        "<tr style='background:#f3f4f6;'>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Business</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Plan</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Status</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Last activity</th>"
        "<th style='padding:8px 12px;border:1px solid #e5e7eb;text-align:left;'>Owner email</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "<h2 style='color:#111827;margin-top:24px;'>Ready-to-send drafts</h2>"
        "<p style='color:#6b7280;'>Copy, personalize, send from your own inbox. "
        "Nothing is sent automatically.</p>"
        f"{drafts_html}"
        "<p style='color:#6b7280;margin-top:16px;'>Full tenant detail: "
        "<a href='https://app.agentnexlify.com/admin/tenant-health' style='color:#3b82f6;'>"
        "app.agentnexlify.com/admin/tenant-health</a></p>"
        "</div>"
    )

    await send_platform_email(subject=subject, body_html=body_html)
    logger.info("churn_watch: alert sent for %d at-risk tenants", count)
