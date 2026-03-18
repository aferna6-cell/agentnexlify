"""Twilio service — missed-call text-back and SMS utilities.

Production webhook URLs must be HTTPS. Use ngrok for local development:
    ngrok http 8000
Then configure Twilio voice webhook to:
    https://<ngrok-id>.ngrok-free.app/api/v1/twilio/missed-call
And messaging webhook to:
    https://<ngrok-id>.ngrok-free.app/api/v1/twilio/sms-reply
"""


import logging
import re

import httpx

from backend.config import settings
from backend.services.retry import with_retry

logger = logging.getLogger(__name__)

# Keywords that signal the caller wants to book an appointment.
BOOKING_KEYWORDS = re.compile(r"\b(appointment|book|schedule)\b", re.IGNORECASE)


async def send_sms(to: str, body: str, from_number: str | None = None) -> bool:
    """Send an SMS via the Twilio REST API."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio not configured — cannot send SMS to %s", to)
        return False

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )

    # Truncate to Twilio's segment-friendly limit.
    if len(body) > 1600:
        body = body[:1597] + "..."

    payload = {
        "From": from_number or settings.twilio_phone_number,
        "To": to,
        "Body": body,
    }

    try:
        async def _do_send():
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    data=payload,
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                )
                resp.raise_for_status()
                return resp

        await with_retry(_do_send, max_retries=2, backoff_base=1.0, label=f"twilio.sms:{to}")
        logger.info("SMS sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send SMS to %s", to)
        return False


def format_textback_message(template: str, business_name: str) -> str:
    """Interpolate {business_name} into the text-back template."""
    return template.replace("{business_name}", business_name)


def looks_like_booking_request(text: str) -> bool:
    """Return True if the message contains booking-related keywords."""
    return bool(BOOKING_KEYWORDS.search(text))
