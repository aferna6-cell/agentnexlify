"""Weekly owner funnel report — Monday email with the platform scoreboard.

Closes the measure-and-iterate loop from audits/audit-post-deploy-measurement-
2026-07-09.md: instead of a manual measurement pass per session, the owner
gets the funnel snapshot every Monday. Numbers come from compute_funnel()
(internal/demo tenants already excluded) and are delivered via the existing
platform mailer, so no new secrets or config are needed.

Dedup: the automation loop's 30-minute tier can fire many times on a Monday,
so a module-level last-sent-date guard limits sends to once per process per
Monday. The core automation tick runs under a cross-worker lock, so in
practice this is once per Monday; a worker restart mid-Monday can at worst
send the owner one duplicate email — accepted for simplicity.

Never raises.
"""

import html
import logging
from datetime import datetime, timezone

from backend.services.funnel_metrics import compute_funnel
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

# Module-level once-per-Monday guard (see module docstring for tradeoff).
_last_sent_date: str | None = None


def _row(label: str, value) -> str:
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    return (
        f"<tr><td style='padding:6px 16px 6px 0;color:#374151;'>{safe_label}</td>"
        f"<td style='padding:6px 0;font-weight:600;color:#111827;'>{safe_value}</td></tr>"
    )


def _rate(value) -> str:
    """Format a percent rate; conversion is unmeasurable when None."""
    return f"{value}%" if value is not None else "n/a"


def _build_report_html(funnel: dict) -> str:
    rows = [
        _row("Real customer tenants", funnel.get("total_tenants", 0)),
        _row("Activated (>=1 chat message)", funnel.get("activated", 0)),
        _row("With at least one lead", funnel.get("with_leads", 0)),
        _row("Paying", funnel.get("paid", 0)),
        _row("New signups this week", funnel.get("new_signups_week", 0)),
        _row("Chat messages this week", funnel.get("new_messages_week", 0)),
        _row("New leads this week", funnel.get("new_leads_week", 0)),
        _row("New appointments this week", funnel.get("new_appointments_week", 0)),
        # The two conversion numbers under active watch since the 2026-06
        # prompt fixes (baseline ~1.0% msg→lead; 2.5% on 07-09; 8.5% on 08-25).
        _row("Msg → lead conversion", _rate(funnel.get("msg_to_lead_rate_week"))),
        _row("Lead → booking conversion", _rate(funnel.get("lead_to_appt_rate_week"))),
    ]
    errors = funnel.get("errors") or []
    error_note = (
        f"<p style='color:#b45309;font-size:13px;'>Metrics that failed to compute: "
        f"{html.escape(', '.join(errors))}</p>"
        if errors
        else ""
    )
    return (
        "<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        "<h2 style='color:#1e293b;'>AgentNexLiFy weekly funnel</h2>"
        "<p style='color:#6b7280;'>Internal and demo tenants excluded. "
        "Weekly counts are Monday-to-now.</p>"
        f"<table style='border-collapse:collapse;'>{''.join(rows)}</table>"
        f"{error_note}"
        "<p style='color:#6b7280;font-size:13px;margin-top:24px;'>"
        "Full breakdown: /admin/funnel, /admin/tenant-health, /admin/referral.</p>"
        "</div>"
    )


async def send_weekly_funnel_report(now: datetime | None = None) -> int:
    """Email the owner the funnel snapshot. Mondays only, once per day.

    Runs in the automation loop's 30-minute tier. Returns 1 when the report
    was sent, 0 otherwise. Never raises.
    """
    global _last_sent_date
    try:
        now = now or datetime.now(timezone.utc)
        if now.weekday() != 0:  # Monday only
            return 0
        today = now.date().isoformat()
        if _last_sent_date == today:
            return 0

        funnel = compute_funnel()
        subject = (
            f"Weekly funnel: {funnel.get('new_signups_week', 0)} signups, "
            f"{funnel.get('new_leads_week', 0)} leads, "
            f"{funnel.get('new_appointments_week', 0)} bookings"
        )
        await send_platform_email(subject=subject, body_html=_build_report_html(funnel))
        _last_sent_date = today
        logger.info("weekly_funnel_report: sent for %s", today)
        return 1
    except Exception:
        logger.warning("weekly_funnel_report: failed", exc_info=True)
        return 0
