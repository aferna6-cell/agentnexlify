"""Email sending service using Resend API with template rendering and rate limiting."""


import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

import resend

from backend.config import settings

logger = logging.getLogger(__name__)

# In-memory daily send tracking per tenant (reset at midnight UTC)
_daily_sends: dict[str, int] = {}
_last_reset_date: str = ""
DAILY_LIMIT = 100
FROM_ADDRESS = "AgentNexLiFy <noreply@agentnexlify.com>"

# Template variable pattern: {{variable_name}}
_TEMPLATE_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def render_template(template: str, context: dict[str, str]) -> str:
    """Replace {{variable}} placeholders with HTML-escaped context values."""
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        value = context.get(key, "")
        return html.escape(str(value))
    return _TEMPLATE_VAR_RE.sub(_replace, template)


def _check_rate_limit(tenant_id: str) -> bool:
    """Return True if tenant is within daily send limit."""
    global _last_reset_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != _last_reset_date:
        _daily_sends.clear()
        _last_reset_date = today
    return _daily_sends.get(tenant_id, 0) < DAILY_LIMIT


def _increment_send_count(tenant_id: str) -> None:
    _daily_sends[tenant_id] = _daily_sends.get(tenant_id, 0) + 1


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Send an email via Resend. Returns result dict with 'success' and 'detail'."""
    if not settings.resend_api_key:
        logger.warning("Resend API key not configured, skipping email to %s", to)
        return {"success": False, "detail": "resend_api_key not configured"}

    if not _check_rate_limit(tenant_id):
        logger.warning("Daily email limit reached for tenant %s", tenant_id)
        return {"success": False, "detail": "daily_limit_reached"}

    try:
        resend.api_key = settings.resend_api_key
        result = resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to],
            "subject": subject,
            "html": body_html,
        })
        _increment_send_count(tenant_id)
        logger.info("Email sent to %s for tenant %s", to, tenant_id)
        return {"success": True, "detail": "sent", "resend_id": result.get("id", "")}
    except Exception as e:
        logger.exception("Failed to send email to %s", to)
        return {"success": False, "detail": str(e)}
