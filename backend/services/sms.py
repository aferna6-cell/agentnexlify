"""Twilio SMS service for inbound/outbound SMS conversations."""

from __future__ import annotations

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


async def send_sms(to: str, body: str) -> bool:
    """Send an SMS via Twilio."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio not configured — cannot send SMS to %s", to)
        return False

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    if len(body) > 1600:
        body = body[:1597] + "..."

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data={
                    "From": settings.twilio_phone_number,
                    "To": to,
                    "Body": body,
                },
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
            resp.raise_for_status()
        logger.info("SMS sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send SMS to %s", to)
        return False
