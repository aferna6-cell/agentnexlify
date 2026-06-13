"""Email the tenant when a new conversation comes in from the website widget.

Opt-in per tenant (``tenants.conversation_email_notify_enabled`` +
``conversation_notify_email``, falling back to ``owner_email``). Fired inline
from the widget chat path the first time a session is seen (``is_new``), as a
background task so it never delays the visitor's reply. Lightweight heads-up:
the visitor's first message + a link to the inbox — not a transcript.
"""

import html
import logging
from typing import Any

from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://app.agentnexlify.com/dashboard/conversations"


def _destination(tenant: dict[str, Any]) -> str | None:
    """Resolve the alert address, or None when the tenant hasn't opted in."""
    if not tenant.get("conversation_email_notify_enabled"):
        return None
    return tenant.get("conversation_notify_email") or tenant.get("owner_email") or None


def build_new_conversation_html(
    business_name: str | None, first_message: str | None
) -> str:
    """Render the 'new conversation started' notification email body."""
    biz = business_name or "your website"
    msg = (first_message or "").strip()
    msg_block = (
        f"<p><strong>First message:</strong><br>{html.escape(msg)}</p>" if msg else ""
    )
    return (
        f"<p>A new conversation just started on your {html.escape(biz)} chat.</p>"
        f"{msg_block}"
        f'<p><a href="{DASHBOARD_URL}">Open the Conversations inbox</a> to reply.</p>'
    )


async def notify_new_conversation(
    tenant: dict[str, Any], first_message: str | None
) -> bool:
    """Email the tenant that a new website conversation started.

    Returns True when an email was sent. Never raises — safe to schedule as a
    FastAPI background task off the widget chat path.
    """
    try:
        dest = _destination(tenant)
        if not dest:
            return False
        biz = tenant.get("business_name")
        await send_email(
            to=dest,
            subject=f"[{biz or 'Your business'}] New website conversation",
            body_html=build_new_conversation_html(biz, first_message),
            tenant_id=tenant.get("id") or "",
        )
        return True
    except Exception:
        logger.warning(
            "notify_new_conversation: failed for tenant %s",
            tenant.get("id"),
            exc_info=True,
        )
        return False
