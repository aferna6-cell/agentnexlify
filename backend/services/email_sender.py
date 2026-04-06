"""Email sending service using Resend API with template rendering and rate limiting."""


import hashlib
import hmac as _hmac
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

import resend

from backend.config import settings
from backend.services.retry import with_retry

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


def render_sms_template(template: str, context: dict[str, str]) -> str:
    """Replace {{variable}} placeholders with plain-text context values (no HTML escaping)."""
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        return str(context.get(key, ""))
    return _TEMPLATE_VAR_RE.sub(_replace, template)


def build_branded_email_html(
    body_html: str,
    branding: dict | None,
    business_name: str = "",
) -> str:
    """Wrap email body in branded HTML template with logo, colors, and footer."""
    if not branding:
        return body_html

    primary = html.escape(branding.get("primary_color", "#00BFFF"))
    logo_url = branding.get("logo_url", "")
    powered_by = html.escape(branding.get("powered_by_text", ""))
    powered_by_url = html.escape(branding.get("powered_by_url", ""))
    biz = html.escape(business_name)

    logo_block = ""
    if logo_url:
        safe_logo = html.escape(logo_url)
        logo_block = (
            f'<img src="{safe_logo}" alt="{biz}" '
            f'style="max-height:48px;max-width:200px;margin-bottom:16px;" />'
        )

    footer_text = powered_by or f"Sent by {biz}"
    footer_block = f"<p>{footer_text}</p>"
    if powered_by_url:
        footer_block = (
            f'<p><a href="{powered_by_url}" style="color:{primary};text-decoration:none;">'
            f'{footer_text}</a></p>'
        )

    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
        '<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:32px 0;">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">'
        f'<tr><td style="background:{primary};padding:24px;text-align:center;">'
        f'{logo_block}<h2 style="color:#fff;margin:0;font-size:20px;">{biz}</h2></td></tr>'
        f'<tr><td style="padding:32px 24px;">{body_html}</td></tr>'
        f'<tr><td style="padding:16px 24px;border-top:1px solid #eee;text-align:center;font-size:12px;color:#999;">'
        f'{footer_block}</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def _make_unsub_sig(lead_id: str, tenant_id: str = "") -> str:
    """HMAC-SHA256 signature for unsubscribe links to prevent abuse.

    Binds to (lead_id, tenant_id) so a signature from one tenant cannot
    be used to unsubscribe a lead belonging to another tenant.
    """
    msg = f"{lead_id}:{tenant_id}" if tenant_id else lead_id
    return _hmac.new(
        settings.api_secret_key.encode(),
        msg.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]


def build_unsubscribe_url(lead_id: str, tenant_id: str) -> str:
    """Build a tenant-bound signed unsubscribe URL for a lead."""
    if not lead_id or not tenant_id:
        raise ValueError("lead_id and tenant_id are required for unsubscribe links")
    sig = _make_unsub_sig(lead_id, tenant_id)
    base = settings.frontend_url.rstrip("/")
    tid_param = f"&tid={tenant_id}"
    return f"{base}/api/v1/widget/unsubscribe?lid={lead_id}{tid_param}&sig={sig}"


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


def _append_unsubscribe_footer(body_html: str, unsubscribe_url: str) -> str:
    """Append an unsubscribe link to the bottom of the email body (CAN-SPAM)."""
    footer = (
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid #eee;'
        'font-size:11px;color:#999;text-align:center;">'
        f'<a href="{html.escape(unsubscribe_url)}" style="color:#999;">Unsubscribe</a>'
        '</div>'
    )
    # Insert before closing </body> or </html> if present, otherwise append
    for tag in ("</body>", "</html>"):
        if tag in body_html:
            return body_html.replace(tag, footer + tag, 1)
    return body_html + footer


def _build_tracking_pixel(tenant_id: str, lead_id: str = "", execution_id: str = "") -> str:
    """Build a 1x1 tracking pixel <img> tag for email open tracking."""
    base = settings.frontend_url.rstrip("/")
    params = f"tid={tenant_id}"
    if lead_id:
        params += f"&lid={lead_id}"
    if execution_id:
        params += f"&eid={execution_id}"
    url = f"{base}/api/v1/widget/track/open?{params}"
    return f'<img src="{html.escape(url)}" width="1" height="1" style="display:none;" alt="" />'


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    tenant_id: str,
    unsubscribe_url: str = "",
    lead_id: str = "",
    execution_id: str = "",
) -> dict[str, Any]:
    """Send an email via Resend. Returns result dict with 'success' and 'detail'."""
    if not settings.resend_api_key:
        logger.warning("Resend API key not configured, skipping email to %s", to)
        return {"success": False, "detail": "resend_api_key not configured"}

    if not _check_rate_limit(tenant_id):
        logger.warning("Daily email limit reached for tenant %s", tenant_id)
        return {"success": False, "detail": "daily_limit_reached"}

    final_html = body_html
    if unsubscribe_url:
        final_html = _append_unsubscribe_footer(body_html, unsubscribe_url)

    # Inject tracking pixel for open tracking
    pixel = _build_tracking_pixel(tenant_id, lead_id, execution_id)
    for tag in ("</body>", "</html>"):
        if tag in final_html:
            final_html = final_html.replace(tag, pixel + tag, 1)
            break
    else:
        final_html += pixel

    resend.api_key = settings.resend_api_key
    send_params: dict[str, Any] = {
        "from": FROM_ADDRESS,
        "to": [to],
        "subject": subject,
        "html": final_html,
    }
    if unsubscribe_url:
        send_params["headers"] = {"List-Unsubscribe": f"<{unsubscribe_url}>"}

    try:
        import asyncio

        # resend.Emails.send is synchronous — run in thread to avoid blocking the
        # event loop and to allow with_retry's async sleep between attempts.
        result = await with_retry(
            lambda: asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send(send_params)
            ),
            max_retries=2,
            backoff_base=1.0,
            label=f"resend.send:{to}",
        )
        _increment_send_count(tenant_id)
        logger.info("Email sent to %s for tenant %s", to, tenant_id)
        return {"success": True, "detail": "sent", "resend_id": result.get("id", "")}
    except Exception as e:
        logger.exception("Failed to send email to %s", to)
        return {"success": False, "detail": str(e)}
