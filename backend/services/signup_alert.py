"""New-signup alert to the founder.

Fires once per new account creation (from the signup side-effects path) so the
founder gets an email the moment a business signs up. Best-effort: never raises,
never blocks signup. Sent to ``settings.signup_alert_email`` (the founder's
inbox), separate from the support inbox.
"""

import html
import logging

from backend.config import settings
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)


async def send_signup_alert(
    *,
    business_name: str,
    owner_name: str,
    email: str,
    industry: str,
    city: str,
) -> dict:
    """Email the founder that a new business signed up. Never raises."""
    recipient = settings.signup_alert_email
    if not recipient:
        logger.warning("signup_alert: signup_alert_email unset; skipping")
        return {"success": False, "detail": "signup_alert_email not configured"}

    biz = html.escape(business_name or "(no name)")
    who = html.escape(owner_name or "(no name)")
    mail = html.escape(email or "(no email)")
    ind = html.escape(industry or "(unknown)")
    loc = html.escape(city or "(unknown)")

    subject = f"New AgentNexLiFy signup: {business_name or 'a business'}"
    body_html = (
        "<h2>New signup</h2>"
        f"<p><strong>{biz}</strong> just created an AgentNexLiFy account.</p>"
        "<ul>"
        f"<li>Owner: {who}</li>"
        f"<li>Email: {mail}</li>"
        f"<li>Industry: {ind}</li>"
        f"<li>City: {loc}</li>"
        "</ul>"
    )

    try:
        return await send_platform_email(subject, body_html, recipient=recipient)
    except Exception:
        logger.warning("signup_alert: send failed for %s", business_name, exc_info=True)
        return {"success": False, "detail": "send failed"}
