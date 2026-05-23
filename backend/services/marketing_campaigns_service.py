"""Marketing campaigns aggregation, query, and AI prompt helpers.

Pulled out of `backend/routers/marketing_campaigns.py` so the router stays
focused on auth + HTTP. Owns recipient queries, analytics compute, and
the prompt scaffolding for the AI email generator.

DB helper accepts `db: Any` so test patches at
`backend.routers.marketing_campaigns.get_service_supabase` still apply.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


VALID_CAMPAIGN_TYPES = {"email", "sms"}
VALID_CAMPAIGN_STATUSES = {"draft", "scheduled", "sending", "sent", "failed"}
VALID_CAMPAIGN_CONTENT_TYPES = {
    "promotional",
    "newsletter",
    "announcement",
    "follow_up",
    "seasonal",
}
MAX_RECIPIENTS_PER_BLAST = 500


class CampaignNotFound(Exception):
    """Raised when a campaign id is not found for a tenant."""


def parse_generated_email(raw: str) -> tuple[str, str]:
    """Parse generated campaign email output into subject/body."""
    subject = ""
    body = raw

    if "SUBJECT:" in raw:
        lines = raw.split("\n", 1)
        first_line = lines[0].strip()
        if first_line.upper().startswith("SUBJECT:"):
            subject = first_line.split(":", 1)[1].strip()
            rest = lines[1] if len(lines) > 1 else ""
            stripped_rest = rest.strip()
            if stripped_rest.startswith("---"):
                body = stripped_rest[3:].strip()
            else:
                body = stripped_rest

    return subject, body


def query_target_leads(
    db: Any, tenant_id: str, target_filter: dict | None
) -> list[dict]:
    """Return up-to-500 leads matching the campaign filter.

    Leads table uses `client_id`, NOT `tenant_id`. Tags filter runs in
    Python because Supabase doesn't expose array overlap on the client.
    """
    query = (
        db.table("leads")
        .select("id, name, email, phone, status, tags, lead_temperature")
        .eq("client_id", tenant_id)
        .eq("unsubscribed", False)
        .order("created_at", desc=True)
        .limit(MAX_RECIPIENTS_PER_BLAST)
    )

    if target_filter:
        if target_filter.get("status"):
            query = query.in_("status", target_filter["status"])
        if target_filter.get("lead_temperature"):
            query = query.in_("lead_temperature", target_filter["lead_temperature"])

    try:
        result = query.execute()
        leads = result.data or []
    except Exception:
        logger.exception("Failed to query target leads for tenant %s", tenant_id)
        return []

    if target_filter and target_filter.get("tags"):
        target_tags = set(target_filter["tags"])
        leads = [
            lead
            for lead in leads
            if lead.get("tags") and set(lead["tags"]) & target_tags
        ]

    return leads


def compute_campaign_analytics(
    db: Any, tenant_id: str, campaign_id: str
) -> dict[str, Any]:
    """Build full analytics payload for one campaign.

    Raises CampaignNotFound if the campaign id is missing/foreign.
    """
    campaign_result = (
        db.table("marketing_campaigns")
        .select(
            "id, name, type, status, total_recipients, total_sent, "
            "total_opened, total_clicked, sent_at"
        )
        .eq("id", campaign_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not campaign_result.data:
        raise CampaignNotFound(campaign_id)

    campaign = campaign_result.data[0]

    sends_result = (
        db.table("campaign_sends")
        .select("id, status, sent_at, opened_at, clicked_at")
        .eq("campaign_id", campaign_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    sends = sends_result.data or []

    by_status: dict[str, int] = {}
    for send in sends:
        s = send["status"]
        by_status[s] = by_status.get(s, 0) + 1

    total_sent = campaign.get("total_sent", 0)
    total_opened = by_status.get("opened", 0) + by_status.get("clicked", 0)
    total_clicked = by_status.get("clicked", 0)

    open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0
    click_rate = round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0

    trend_data = _compute_trend_data(db, tenant_id, campaign_id, campaign.get("sent_at"))
    device_breakdown = _compute_device_breakdown(db, tenant_id, campaign_id)

    return {
        "campaign": campaign,
        "total_sent": total_sent,
        "total_opened": total_opened,
        "total_clicked": total_clicked,
        "total_bounced": by_status.get("bounced", 0),
        "total_failed": by_status.get("failed", 0),
        "open_rate": open_rate,
        "click_rate": click_rate,
        "by_status": by_status,
        "trend_data": trend_data,
        "device_breakdown": device_breakdown,
    }


def _compute_trend_data(
    db: Any, tenant_id: str, campaign_id: str, sent_at: str | None
) -> list[dict]:
    """Daily opens/clicks for up to 30 days since send."""
    if not sent_at:
        return []
    trend_data: list[dict] = []
    try:
        sent_date = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
        days_since_sent = (datetime.now(timezone.utc) - sent_date).days
        lookback = min(days_since_sent, 30)
        if lookback <= 0:
            return []
        trend_start = (
            (datetime.now(timezone.utc) - timedelta(days=lookback)).date().isoformat()
        )
        email_events_result = (
            db.table("email_events")
            .select("event_type, created_at")
            .eq("campaign_tag", campaign_id)
            .eq("tenant_id", tenant_id)
            .gte("created_at", trend_start)
            .execute()
        )
        events = email_events_result.data or []
        date_event_map: dict[str, dict] = {}
        for evt in events:
            date_key = evt.get("created_at", "")[:10]
            if date_key not in date_event_map:
                date_event_map[date_key] = {"opens": 0, "clicks": 0}
            if evt.get("event_type") == "open":
                date_event_map[date_key]["opens"] += 1
            elif evt.get("event_type") == "click":
                date_event_map[date_key]["clicks"] += 1

        for i in range(lookback + 1):
            date = (
                datetime.now(timezone.utc).date() - timedelta(days=i)
            ).isoformat()
            data = date_event_map.get(date, {"opens": 0, "clicks": 0})
            trend_data.append(
                {"date": date, "opens": data["opens"], "clicks": data["clicks"]}
            )
        trend_data.reverse()
    except Exception:
        logger.warning(
            "Failed to load trend data for campaign %s", campaign_id, exc_info=True
        )
    return trend_data


def _compute_device_breakdown(
    db: Any, tenant_id: str, campaign_id: str
) -> dict[str, int]:
    """Mobile/desktop/other split derived from email_events.details."""
    device_breakdown: dict[str, int] = {}
    try:
        email_events_result = (
            db.table("email_events")
            .select("details")
            .eq("campaign_tag", campaign_id)
            .eq("tenant_id", tenant_id)
            .limit(500)
            .execute()
        )
        for evt in email_events_result.data or []:
            details = evt.get("details") or {}
            device = details.get("device") or details.get("user_agent", "unknown")
            if "iPhone" in device or "Android" in device:
                device_breakdown["mobile"] = device_breakdown.get("mobile", 0) + 1
            elif "Desktop" in device or "computer" in device.lower():
                device_breakdown["desktop"] = device_breakdown.get("desktop", 0) + 1
            else:
                device_breakdown["other"] = device_breakdown.get("other", 0) + 1
    except Exception:
        logger.warning(
            "Failed to load device breakdown for campaign %s",
            campaign_id,
            exc_info=True,
        )
    return device_breakdown


TYPE_INSTRUCTIONS: dict[str, str] = {
    "promotional": "Create a compelling promotional email that highlights a special offer or service. Include urgency and a clear call to action.",
    "newsletter": "Create an engaging newsletter that provides value through tips, updates, or industry insights. Keep it informative and helpful.",
    "announcement": "Create a professional announcement email about something new or noteworthy. Build excitement while being clear and concise.",
    "follow_up": "Create a warm follow-up email that re-engages leads who haven't responded. Be friendly, not pushy. Reference their earlier interest.",
    "seasonal": "Create a seasonal or holiday-themed email that ties the business to current events or seasons. Be festive but professional.",
}


def build_email_system_prompt(
    business_name: str, business_type: str | None, campaign_type: str, tone: str
) -> str:
    """Construct the system prompt for the AI email generator."""
    biz_context = f" for {business_name}" + (
        f", a {business_type}" if business_type else ""
    )
    return (
        f"You are an email marketing expert creating campaign emails{biz_context}. "
        f"{TYPE_INSTRUCTIONS.get(campaign_type, '')} "
        f"Tone: {tone}.\n\n"
        "Return the email in this exact format:\n"
        "SUBJECT: [the email subject line]\n"
        "---\n"
        "[the email body in HTML format with proper tags like <h2>, <p>, <a>, etc.]\n\n"
        "The email body should be 150-300 words. Use clean, responsive-friendly HTML. "
        "Include a clear call to action. Do not include <html>, <head>, or <body> tags -- just the inner content."
    )
