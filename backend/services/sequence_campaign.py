"""One-time campaign blast for lead re-engagement.

Pulled out of `send_campaign` in the sequences router so the handler
stays focused on auth + HTTP. Owns the filtered-leads query, CAN-SPAM
filter, and per-channel dispatch (email or SMS).

DB helper accepts `db: Any` so test patches at
`backend.routers.sequences.get_service_supabase` still apply.
"""

from typing import Any

from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms


def fetch_campaign_leads(
    db: Any, tenant_id: str, filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return up-to-500 leads matching the campaign filters minus unsubscribed.

    Filters (all optional): status, min_score, created_after, created_before, tags.
    Tags filter runs in Python — Supabase client doesn't expose array overlap.
    Leads table uses `client_id`, NOT `tenant_id`.
    """
    query = (
        db.table("leads")
        .select("id, name, email, phone, unsubscribed, tags")
        .eq("client_id", tenant_id)
    )

    if filters.get("status"):
        query = query.eq("status", filters["status"])
    if filters.get("min_score"):
        query = query.gte("lead_score", filters["min_score"])
    if filters.get("created_after"):
        query = query.gte("created_at", filters["created_after"])
    if filters.get("created_before"):
        query = query.lte("created_at", filters["created_before"])

    result = query.limit(500).execute()
    leads = result.data or []

    if filters.get("tags"):
        required_tags = set(filters["tags"])
        leads = [l for l in leads if set(l.get("tags") or []) & required_tags]

    return [l for l in leads if not l.get("unsubscribed")]


async def dispatch_campaign(
    leads: list[dict[str, Any]],
    *,
    tenant_id: str,
    channel: str,
    subject: str,
    body_html: str,
    plan: str,
) -> dict[str, int]:
    """Send the campaign over `channel` and return {total, sent, skipped}.

    Email path: builds an unsubscribe URL per lead and calls `send_email`.
    SMS path: checks per-tenant rate limit, calls `send_sms`, increments counter.
    """
    sent = 0
    skipped = 0

    for lead in leads:
        if channel == "email":
            if not lead.get("email"):
                skipped += 1
                continue
            unsub_url = build_unsubscribe_url(lead["id"], tenant_id)
            email_result = await send_email(
                to=lead["email"],
                subject=subject,
                body_html=body_html,
                tenant_id=tenant_id,
                unsubscribe_url=unsub_url,
            )
            if email_result.get("success"):
                sent += 1
            else:
                skipped += 1
        elif channel == "sms":
            if not lead.get("phone"):
                skipped += 1
                continue
            if not check_sms_rate_limit(tenant_id, plan):
                skipped += 1
                continue
            sms_ok = await send_sms(to=lead["phone"], body=body_html)
            if sms_ok:
                sent += 1
                increment_sms_count(tenant_id)
            else:
                skipped += 1

    return {"total_leads": len(leads), "sent": sent, "skipped": skipped}
