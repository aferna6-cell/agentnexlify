"""Tenant-silence watch — ops alert when a paying tenant goes quiet.

Funnel audit 2026-07-23: Keys Koffee's site redeploy dropped the widget embed
around 2026-06-14 and a PAYING tenant sat at zero conversations for 5+ weeks
before a manual audit noticed. This job is the alarm that closes that class of
gap (bug-patterns.md: "Silent-green automation"): any tenant on a paid plan
with an active subscription whose latest conversation is older than
SILENCE_DAYS — or who has never had one and signed up more than SILENCE_DAYS
ago — triggers an ops email to the platform operator.

Recipient resolution: platform_settings key ``platform_alert_email`` (DB
override, migration-175 machinery) → env ``PLATFORM_ALERT_EMAIL`` →
support@agentnexlify.com. Dedup: an ``activity_log`` row of type
``tenant_silence_alert`` suppresses re-alerts for REALERT_DAYS, so a silent
tenant nags every few days instead of every 30-minute tick.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)

# Paid plans per CLAUDE.md: current (chatbot, agent_os) + grandfathered legacy.
PAID_PLANS = ["chatbot", "agent_os", "growth", "autopilot", "professional", "enterprise"]
ACTIVE_STATUSES = ["active", "trialing"]
SILENCE_DAYS = 7
REALERT_DAYS = 3
ALERT_ACTIVITY_TYPE = "tenant_silence_alert"
DEFAULT_ALERT_EMAIL = "support@agentnexlify.com"


def _alert_recipient() -> str:
    try:
        from backend.services.platform_flags import flag_value

        override = flag_value("platform_alert_email")
        if override:
            return override.strip()
    except Exception:
        logger.warning("platform_alert_email flag lookup failed", exc_info=True)
    return os.environ.get("PLATFORM_ALERT_EMAIL", "").strip() or DEFAULT_ALERT_EMAIL


def _recently_alerted(db, tenant_id: str, since_iso: str) -> bool:
    try:
        result = (
            db.table("activity_log")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", ALERT_ACTIVITY_TYPE)
            .gte("created_at", since_iso)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        # Dedup lookup failing must not suppress the alert (fail-noisy).
        logger.warning("silence-watch dedup lookup failed tenant=%s", tenant_id, exc_info=True)
        return False


def _last_conversation_at(db, tenant_id: str) -> str | None:
    # conversations is client_id-scoped (NOT tenant_id) — schema-discipline.md.
    result = (
        db.table("conversations")
        .select("created_at")
        .eq("client_id", tenant_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0]["created_at"] if result.data else None


async def check_tenant_silence() -> int:
    """Alert the platform operator about paying tenants silent for SILENCE_DAYS.

    Returns the number of alerts sent this run.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    silence_cutoff = now - timedelta(days=SILENCE_DAYS)
    realert_cutoff_iso = (now - timedelta(days=REALERT_DAYS)).isoformat()
    alerts_sent = 0

    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status, created_at, is_demo")
            .in_("plan", PAID_PLANS)
            .in_("plan_status", ACTIVE_STATUSES)
            .execute()
        ).data or []
    except Exception:
        logger.exception("silence-watch: tenant query failed")
        return 0

    recipient = _alert_recipient()

    for tenant in tenants:
        if tenant.get("is_demo"):
            continue
        tenant_id = tenant["id"]
        try:
            created_at = datetime.fromisoformat(
                str(tenant.get("created_at")).replace("Z", "+00:00")
            )
            if created_at > silence_cutoff:
                continue  # too new to judge

            last_conv_iso = _last_conversation_at(db, tenant_id)
            if last_conv_iso is not None:
                last_conv = datetime.fromisoformat(last_conv_iso.replace("Z", "+00:00"))
                if last_conv > silence_cutoff:
                    continue  # healthy

            if _recently_alerted(db, tenant_id, realert_cutoff_iso):
                continue

            days_silent = (
                (now - datetime.fromisoformat(last_conv_iso.replace("Z", "+00:00"))).days
                if last_conv_iso
                else (now - created_at).days
            )
            name = tenant.get("business_name") or tenant_id
            subject = f"[silence-watch] {name}: no conversations in {days_silent} days"
            body_html = (
                f"<p><strong>{name}</strong> (plan {tenant.get('plan')}) has had "
                f"no widget conversations in <strong>{days_silent} days</strong>."
                f"{' They have NEVER had a conversation.' if not last_conv_iso else ''}</p>"
                "<p>Most likely causes, in order: the widget embed was removed from "
                "their site (check the site HTML for the script tag), the site moved, "
                "or their traffic dropped. Keys Koffee lost its embed for 5+ weeks "
                "before anyone noticed — that is why this alert exists.</p>"
                f"<p>Tenant id: {tenant_id}</p>"
            )
            result = await send_email(
                to=recipient, subject=subject, body_html=body_html, tenant_id=tenant_id
            )
            log_activity(
                tenant_id=tenant_id,
                activity_type=ALERT_ACTIVITY_TYPE,
                description=f"Silence alert sent to {recipient} ({days_silent}d silent)",
                metadata={
                    "days_silent": days_silent,
                    "recipient": recipient,
                    "email_success": bool(result.get("success")),
                },
            )
            alerts_sent += 1
        except Exception:
            logger.warning(
                "silence-watch: check failed tenant=%s", tenant_id, exc_info=True
            )

    if alerts_sent:
        logger.info("silence-watch: sent %d alert(s)", alerts_sent)
    return alerts_sent
