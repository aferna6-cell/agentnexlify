"""Calendly API integration (placeholder for future implementation)."""

from __future__ import annotations

import logging

from backend.config import settings

logger = logging.getLogger(__name__)


async def create_calendly_event(
    calendly_link: str,
    lead_name: str,
    lead_email: str | None,
    preferred_date: str | None,
    preferred_time: str | None,
    event_type: str = "consultation_call",
) -> dict:
    """Create a Calendly scheduling link or event.

    For MVP, we just return the agent's Calendly link for manual booking.
    Full API integration can be added later with the Calendly API v2.
    """
    if not settings.calendly_api_key:
        logger.info("Calendly API not configured — returning link for manual booking")
        return {
            "success": True,
            "booking_url": calendly_link,
            "message": "Lead should use the Calendly link to book.",
        }

    # Future: use Calendly API to create a one-time scheduling link
    # POST https://api.calendly.com/scheduling_links
    logger.info("Calendly API integration not yet implemented")
    return {
        "success": True,
        "booking_url": calendly_link,
        "message": "Lead should use the Calendly link to book.",
    }
