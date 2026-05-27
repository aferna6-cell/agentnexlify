"""Daily briefing SMS — morning summary text to business owners.

Sends a concise SMS with:
  - New leads since yesterday
  - Today's appointments
  - Pending action items / overdue tasks
  - Recent review alerts

Runs on the 30-min automation tier. Checks each tenant's timezone so
the SMS arrives around 8 AM local time.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.models.database import get_service_supabase
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

BATCH_LIMIT = 100

# Only send briefing between 7:30 and 8:30 local time
BRIEFING_HOUR_START = 7
BRIEFING_MINUTE_START = 30
BRIEFING_HOUR_END = 8
BRIEFING_MINUTE_END = 30


def _is_briefing_window(tz_name: str, now_utc: datetime) -> bool:
    """Return True if current local time is within the morning briefing window."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/New_York")
    local_now = now_utc.astimezone(tz)
    local_minutes = local_now.hour * 60 + local_now.minute
    start = BRIEFING_HOUR_START * 60 + BRIEFING_MINUTE_START
    end = BRIEFING_HOUR_END * 60 + BRIEFING_MINUTE_END
    return start <= local_minutes < end


async def send_daily_briefings() -> int:
    """Send morning briefing SMS to all tenants with the feature enabled.

    Returns count of briefings sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    today_iso = now.date().isoformat()
    sent = 0

    # Get tenants with daily briefing enabled and a phone number
    try:
        tenants = (
            db.table("tenants")
            .select(
                "id, business_name, notification_phone, sms_notifications_enabled, "
                "plan, owner_email, daily_briefing_enabled"
            )
            .eq("daily_briefing_enabled", True)
            .eq("sms_notifications_enabled", True)
            .filter("notification_phone", "not.is", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_daily_briefings: failed to query tenants")
        return 0

    for tenant in tenants.data or []:
        tenant_id = str(tenant["id"])
        phone = tenant.get("notification_phone")
        plan = tenant.get("plan") or "free"
        biz_name = tenant.get("business_name") or "Your business"

        if not phone:
            continue

        # Check if this tenant already got a briefing today (dedup via activity_log)
        try:
            dedup = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("action", "daily_briefing_sent")
                .gte("created_at", today_iso)
                .limit(1)
                .execute()
            )
            if dedup.data:
                continue  # Already sent today
        except Exception:
            logger.debug(
                "Briefing dedup check failed for %s, proceeding",
                tenant_id,
                exc_info=True,
            )

        # Determine timezone from business_hours config
        tz_name = "America/New_York"
        try:
            bh = (
                db.table("business_hours")
                .select("timezone")
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            if bh.data:
                tz_name = bh.data[0].get("timezone") or tz_name
        except Exception:
            logger.debug(
                "Failed to load business_hours timezone for tenant %s, defaulting to %s",
                tenant_id,
                tz_name,
                exc_info=True,
            )

        # Only send during morning window in tenant's timezone
        if not _is_briefing_window(tz_name, now):
            continue

        # Rate limit check
        if not check_sms_rate_limit(tenant_id, plan):
            continue

        # Gather briefing data
        try:
            briefing = await _build_briefing(db, tenant_id, tz_name, now)
        except Exception:
            logger.warning(
                "Failed to build briefing for tenant %s", tenant_id, exc_info=True
            )
            continue

        # Compose SMS
        sms_body = _format_briefing_sms(biz_name, briefing)

        # Send
        try:
            ok = await send_sms(to=phone, body=sms_body)
            if ok:
                increment_sms_count(tenant_id)
                sent += 1
                # Log for dedup
                db.table("activity_log").insert(
                    {
                        "tenant_id": tenant_id,
                        "action": "daily_briefing_sent",
                        "description": f"Daily briefing SMS sent to {phone}",
                    }
                ).execute()
                logger.info("Daily briefing sent to tenant %s", tenant_id)
        except Exception:
            logger.exception(
                "Failed to send daily briefing SMS to tenant %s", tenant_id
            )

    return sent


async def _build_briefing(db, tenant_id: str, tz_name: str, now: datetime) -> dict:
    """Gather metrics for the briefing: leads, appointments, tasks, reviews."""
    yesterday = (now - timedelta(hours=24)).isoformat()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/New_York")
    local_today = now.astimezone(tz).date()
    today_start = datetime.combine(local_today, datetime.min.time(), tzinfo=tz)
    today_end = datetime.combine(local_today, datetime.max.time(), tzinfo=tz)

    briefing: dict = {}

    # New leads (last 24h)
    try:
        leads = (
            tenant_table(db, "leads", tenant_id)
            .select("id", count="exact")
            .gte("created_at", yesterday)
            .execute()
        )
        briefing["new_leads"] = (
            leads.count if leads.count is not None else len(leads.data or [])
        )
    except Exception:
        briefing["new_leads"] = 0

    # Today's appointments
    try:
        appts = (
            tenant_table(db, "appointments", tenant_id)
            .select("id, customer_name, start_time, status")
            .gte("start_time", today_start.astimezone(timezone.utc).isoformat())
            .lte("start_time", today_end.astimezone(timezone.utc).isoformat())
            .neq("status", "cancelled")
            .order("start_time")
            .execute()
        )
        briefing["appointments"] = appts.data or []
        briefing["appointment_count"] = len(briefing["appointments"])
    except Exception:
        briefing["appointments"] = []
        briefing["appointment_count"] = 0

    # Pending action items
    try:
        actions = (
            tenant_table(db, "action_items", tenant_id)
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        briefing["pending_actions"] = (
            actions.count if actions.count is not None else len(actions.data or [])
        )
    except Exception:
        briefing["pending_actions"] = 0

    # Unread conversations (handoff or unread)
    try:
        convos = (
            db.table("conversations")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .eq("is_read", False)
            .execute()
        )
        briefing["unread_convos"] = (
            convos.count if convos.count is not None else len(convos.data or [])
        )
    except Exception:
        briefing["unread_convos"] = 0

    return briefing


def _format_appointment_time(start_time: str | None) -> str:
    """Return a portable appointment time like 1:30 PM, or empty on parse fail."""
    if not start_time:
        return ""
    try:
        parsed = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except Exception:
        logger.debug(
            "Failed to parse appointment start_time %r", start_time, exc_info=True
        )
        return ""
    return parsed.strftime("%I:%M %p").lstrip("0")


def _format_briefing_sms(business_name: str, b: dict) -> str:
    """Format briefing data into a concise SMS message."""
    lines = [f"Good morning! Here's your {business_name} daily briefing:"]

    # Leads
    n = b.get("new_leads", 0)
    if n > 0:
        lines.append(f"📬 {n} new lead{'s' if n != 1 else ''}")
    else:
        lines.append("📬 No new leads")

    # Appointments
    ac = b.get("appointment_count", 0)
    if ac > 0:
        lines.append(f"📅 {ac} appointment{'s' if ac != 1 else ''} today")
        # Show first 3
        for appt in b.get("appointments", [])[:3]:
            name = appt.get("customer_name") or "Customer"
            time_str = _format_appointment_time(appt.get("start_time"))
            lines.append(f"  • {time_str} — {name}" if time_str else f"  • {name}")
        if ac > 3:
            lines.append(f"  + {ac - 3} more")
    else:
        lines.append("📅 No appointments today")

    # Action items
    pa = b.get("pending_actions", 0)
    if pa > 0:
        lines.append(f"⚡ {pa} pending task{'s' if pa != 1 else ''}")

    # Unread conversations
    uc = b.get("unread_convos", 0)
    if uc > 0:
        lines.append(f"💬 {uc} unread conversation{'s' if uc != 1 else ''}")

    lines.append("\nOpen your dashboard to see details.")

    return "\n".join(lines)
