"""Transactional email to the platform owner.

Used by the support form, the Agent OS fail/abstain alert, and the support
chatbot. Distinct from ``email_sender.send_email`` (tenant marketing mail):

- recipient is always the platform owner (``PLATFORM_SUPPORT_EMAIL``),
- no open-tracking pixel, no unsubscribe footer,
- no per-tenant daily quota and no demo-tenant suppression,
- supports file attachments (e.g. conversation transcripts).

Never raises — every sender is best-effort and returns a result dict.
"""

import asyncio
import base64
import logging
from typing import Any

import resend

from backend.config import settings
from backend.services.retry import with_retry

logger = logging.getLogger(__name__)

FROM_ADDRESS = "AgentNexLiFy <noreply@agentnexlify.com>"


def text_attachment(filename: str, text: str) -> dict[str, str]:
    """Build a Resend attachment dict from plain text (base64-encoded content)."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return {"filename": filename, "content": encoded}


async def send_platform_email(
    subject: str,
    body_html: str,
    attachments: list[dict[str, Any]] | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """Send a transactional email to the platform owner. Never raises."""
    recipient = settings.platform_support_email
    if not recipient:
        logger.warning("platform_mailer: PLATFORM_SUPPORT_EMAIL unset; skipping send")
        return {"success": False, "detail": "platform_support_email not configured"}
    if not settings.resend_api_key:
        logger.warning("platform_mailer: resend_api_key not configured; skipping send")
        return {"success": False, "detail": "resend_api_key not configured"}

    resend.api_key = settings.resend_api_key
    params: dict[str, Any] = {
        "from": FROM_ADDRESS,
        "to": [recipient],
        "subject": subject,
        "html": body_html,
    }
    if attachments:
        params["attachments"] = attachments
    if reply_to:
        params["reply_to"] = reply_to

    try:
        # resend.Emails.send is synchronous — run in a thread so the event loop
        # stays free and with_retry's async backoff works between attempts.
        result = await with_retry(
            lambda: asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send(params)
            ),
            max_retries=2,
            backoff_base=1.0,
            label="resend.platform_send",
        )
        logger.info("platform email sent: %s", subject)
        return {"success": True, "detail": "sent", "resend_id": result.get("id", "")}
    except Exception as e:
        logger.exception("platform_mailer: send failed")
        return {"success": False, "detail": str(e)}
