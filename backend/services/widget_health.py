"""Pure probe logic for the widget / integration health check.

No FastAPI imports. Each probe is wrapped in its own try/except so a single
failing probe never 500-errors the whole response.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


def _overall(checks: list[dict]) -> str:
    """Derive overall status from an ordered list of check dicts.

    Returns "not_ready" if any check is "fail", "needs_attention" if any
    check is "warn", and "healthy" otherwise.
    """
    statuses = [c.get("status") for c in checks]
    if "fail" in statuses:
        return "not_ready"
    if "warn" in statuses:
        return "needs_attention"
    return "healthy"


def compute_widget_health(tenant_id: str) -> dict:
    """Run all health probes for *tenant_id* and return a structured result.

    Returns:
        {
            "overall": "healthy" | "needs_attention" | "not_ready",
            "checks": [{"id", "label", "status", "detail", "action"}, ...],
            "allowed_domains": [...],
            "stats": {"leads_7d": int, "conversations_7d": int, "appointments_7d": int},
        }
    """
    db = get_service_supabase()
    checks: list[dict] = []

    # ── Probe 1: widget_installed ──────────────────────────────────────────
    widget_row = None
    try:
        result = (
            db.table("widget_configs")
            .select("tenant_id, allowed_domains")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            widget_row = result.data[0]
            checks.append(
                {
                    "id": "widget_installed",
                    "label": "Widget installed",
                    "status": "ok",
                    "detail": "Widget config found.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "widget_installed",
                    "label": "Widget installed",
                    "status": "fail",
                    "detail": "No widget config found — finish onboarding.",
                    "action": {"label": "Open setup", "target": "widget"},
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'widget_installed' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "widget_installed",
                "label": "Widget installed",
                "status": "fail",
                "detail": "Could not verify widget config.",
                "action": {"label": "Open setup", "target": "widget"},
            }
        )

    # ── Probe 2: allowed_domains ───────────────────────────────────────────
    current_allowed_domains: list = []
    try:
        domains = (widget_row or {}).get("allowed_domains") or []
        current_allowed_domains = domains if isinstance(domains, list) else []
        if current_allowed_domains:
            checks.append(
                {
                    "id": "allowed_domains",
                    "label": "Allowed domains",
                    "status": "ok",
                    "detail": f"{len(current_allowed_domains)} domain(s) configured.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "allowed_domains",
                    "label": "Allowed domains",
                    "status": "warn",
                    "detail": "Widget accepts requests from any domain. Lock it down to your site.",
                    "action": {
                        "label": "Edit domains",
                        "target": "integration_health",
                    },
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'allowed_domains' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "allowed_domains",
                "label": "Allowed domains",
                "status": "fail",
                "detail": "Could not verify allowed domains.",
                "action": None,
            }
        )

    # ── Probe 3: calendar ──────────────────────────────────────────────────
    try:
        result = (
            db.table("integrations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .in_("provider", ["google_calendar", "m365_calendar"])
            .limit(1)
            .execute()
        )
        if result.data:
            checks.append(
                {
                    "id": "calendar",
                    "label": "Calendar connected",
                    "status": "ok",
                    "detail": "Calendar integration active.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "calendar",
                    "label": "Calendar connected",
                    "status": "warn",
                    "detail": "No calendar linked — booking falls back to manual.",
                    "action": {"label": "Connect calendar", "target": "integrations"},
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'calendar' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "calendar",
                "label": "Calendar connected",
                "status": "fail",
                "detail": "Could not verify calendar integration.",
                "action": None,
            }
        )

    # ── Probe 4: email ─────────────────────────────────────────────────────
    try:
        if getattr(settings, "resend_api_key", ""):
            checks.append(
                {
                    "id": "email",
                    "label": "Email delivery",
                    "status": "ok",
                    "detail": "Resend configured.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "email",
                    "label": "Email delivery",
                    "status": "warn",
                    "detail": "Email follow-ups disabled until email is configured.",
                    "action": None,
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'email' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "email",
                "label": "Email delivery",
                "status": "fail",
                "detail": "Could not verify email configuration.",
                "action": None,
            }
        )

    # ── Probe 5: first_automation ──────────────────────────────────────────
    try:
        result = (
            db.table("activity_log")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            checks.append(
                {
                    "id": "first_automation",
                    "label": "First automation fired",
                    "status": "ok",
                    "detail": "Automations are live.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "first_automation",
                    "label": "First automation fired",
                    "status": "warn",
                    "detail": "No automation has fired yet. This is the activation milestone.",
                    "action": {
                        "label": "View automations",
                        "target": "automations",
                    },
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'first_automation' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "first_automation",
                "label": "First automation fired",
                "status": "fail",
                "detail": "Could not verify automation history.",
                "action": None,
            }
        )

    # ── Probe 6: recent_activity ───────────────────────────────────────────
    leads_7d = 0
    conversations_7d = 0
    appointments_7d = 0
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # leads uses client_id
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("created_at", cutoff)
            .execute()
        )
        leads_7d = leads_result.count or 0

        # conversations uses client_id
        conv_result = (
            db.table("conversations")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("created_at", cutoff)
            .execute()
        )
        conversations_7d = conv_result.count or 0

        # appointments uses tenant_id
        appt_result = (
            db.table("appointments")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", cutoff)
            .execute()
        )
        appointments_7d = appt_result.count or 0

        if leads_7d + conversations_7d > 0:
            checks.append(
                {
                    "id": "recent_activity",
                    "label": "Recent activity (7 days)",
                    "status": "ok",
                    "detail": f"{leads_7d} lead(s) and {conversations_7d} conversation(s) in the last 7 days.",
                    "action": None,
                }
            )
        else:
            checks.append(
                {
                    "id": "recent_activity",
                    "label": "Recent activity (7 days)",
                    "status": "warn",
                    "detail": "No new leads or chats in the last 7 days.",
                    "action": None,
                }
            )
    except Exception:
        logger.warning(
            "widget_health probe 'recent_activity' failed for tenant=%s",
            tenant_id,
            exc_info=True,
        )
        checks.append(
            {
                "id": "recent_activity",
                "label": "Recent activity (7 days)",
                "status": "fail",
                "detail": "Could not fetch recent activity.",
                "action": None,
            }
        )

    return {
        "overall": _overall(checks),
        "checks": checks,
        "allowed_domains": current_allowed_domains,
        "stats": {
            "leads_7d": leads_7d,
            "conversations_7d": conversations_7d,
            "appointments_7d": appointments_7d,
        },
    }
