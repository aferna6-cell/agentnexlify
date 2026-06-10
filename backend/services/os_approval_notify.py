"""Owner notification when an Agent OS deliverable awaits approval.

Gap fix (2026-06-10): drafts landed in pending_approval silently — the owner
only discovered them by opening the dashboard, so approvals rotted and the
AI staff looked stalled. Now the owner gets an email the moment a draft
needs them, throttled so a burst of drafts doesn't flood the inbox.

Best-effort by design: a notification failure must never break the chat turn.
"""

import logging
import time

from backend.config import settings
from backend.services.email_sender import send_email, mask_email
from backend.services.tenant_scope import tenant_table

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
            .select("owner_email, owner_name, business_name")
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

        what = title or f"a {channel or 'message'} draft"
        extra = (
            f"<p>You have {pending_count} items waiting in total.</p>"
            if pending_count > 1
            else ""
        )
        await send_email(
            to=owner_email,
            subject=f"Your AI staff needs a quick approval ({pending_count} waiting)",
            body_html=(
                f"<p>Hi {rows[0].get('owner_name') or 'there'},</p>"
                f"<p>Your <strong>{agent_name}</strong> agent prepared "
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
        return True
    except Exception:
        logger.warning(
            "os_approval_notify: failed for tenant %s — turn unaffected",
            tenant_id,
            exc_info=True,
        )
        return False
