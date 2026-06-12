"""Owner notification when an Agent OS deliverable awaits approval.

Gap fix (2026-06-10): drafts landed in pending_approval silently — the owner
only discovered them by opening the dashboard, so approvals rotted and the
AI staff looked stalled. Now the owner gets an email the moment a draft
needs them, throttled so a burst of drafts doesn't flood the inbox.

Best-effort by design: a notification failure must never break the chat turn.
"""

import html
import logging
import time

from backend.config import settings
from backend.services.email_sender import send_email, mask_email
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

# Per-process throttle: at most one approval email per tenant per window.
# 4 Uvicorn workers → worst case 4 emails per window; acceptable best-effort
# (matches the in-memory cache pattern documented in python-fastapi.md).
_THROTTLE_SECONDS = 30 * 60
_last_sent: dict[str, float] = {}


def _throttled(tenant_id: str, now: float) -> bool:
    last = _last_sent.get(tenant_id)
    return last is not None and (now - last) < _THROTTLE_SECONDS


async def notify_pending_approval(
    db,
    tenant_id: str,
    *,
    agent_name: str,
    channel: str | None,
    title: str | None,
) -> bool:
    """Email the owner that a draft awaits approval. Returns True if sent."""
    now = time.time()
    if _throttled(tenant_id, now):
        return False
    try:
        result = (
            db.table("tenants")
            .select(
                "owner_email, owner_name, business_name, "
                "notification_phone, sms_notifications_enabled"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        owner_email = rows[0].get("owner_email")
        if not owner_email:
            return False

        pending = (
            tenant_table(db, "os_agent_runs", tenant_id)
            .select("id", count="exact")
            .eq("deliverable_status", "pending_approval")
            .execute()
        )
        pending_count = pending.count or 1

        # Escape everything interpolated into HTML: the draft title can echo
        # customer-supplied chat content (HTML-injection vector into the
        # owner's inbox), and owner/agent names are tenant-supplied.
        safe_owner = html.escape(rows[0].get("owner_name") or "there")
        safe_agent = html.escape(agent_name or "assistant")
        what = html.escape(title) if title else f"a {html.escape(channel or 'message')} draft"
        count_n = int(pending_count)
        extra = (
            f"<p>You have {count_n} items waiting in total.</p>"
            if count_n > 1
            else ""
        )
        await send_email(
            to=owner_email,
            subject=f"Your AI staff needs a quick approval ({count_n} waiting)",
            body_html=(
                f"<p>Hi {safe_owner},</p>"
                f"<p>Your <strong>{safe_agent}</strong> agent prepared "
                f"<strong>{what}</strong> and is waiting for your go-ahead "
                "before anything is sent.</p>"
                f"{extra}"
                f'<p><a href="{settings.frontend_url}/dashboard/agent-os" '
                'style="background:#3b82f6;color:#fff;padding:10px 20px;'
                'border-radius:6px;text-decoration:none;font-weight:600;">'
                "Review &amp; approve &rarr;</a></p>"
                "<p>Nothing goes out to your customers without your approval "
                "unless you turn on auto-send in Settings.</p>"
            ),
            tenant_id=tenant_id,
        )
        _last_sent[tenant_id] = now
        logger.info(
            "os_approval_notify: emailed %s for tenant %s (pending=%s)",
            mask_email(owner_email),
            tenant_id,
            pending_count,
        )

        # SMS leg — the owner is usually away from email when a customer is
        # waiting. Opt-in via sms_notifications_enabled + notification_phone
        # (same toggle that gates missed-call texts). Shares the email's
        # 30-min throttle window; its own failure never voids the email send.
        phone = rows[0].get("notification_phone")
        if phone and rows[0].get("sms_notifications_enabled"):
            try:
                plain_what = title or f"a {channel or 'message'} draft"
                sms_body = (
                    f"AgentNexLiFy: your {agent_name or 'assistant'} agent drafted "
                    f"{plain_what} and needs your approval before it sends. "
                    f"Review: {settings.frontend_url}/dashboard/agent-os"
                )
                await send_sms(to=phone, body=sms_body, tenant_id=tenant_id)
                logger.info(
                    "os_approval_notify: SMS sent for tenant %s (phone ...%s)",
                    tenant_id,
                    str(phone)[-4:],
                )
            except Exception:
                logger.warning(
                    "os_approval_notify: SMS leg failed for tenant %s — email already sent",
                    tenant_id,
                    exc_info=True,
                )
        return True
    except Exception:
        logger.warning(
            "os_approval_notify: failed for tenant %s — turn unaffected",
            tenant_id,
            exc_info=True,
        )
        return False
