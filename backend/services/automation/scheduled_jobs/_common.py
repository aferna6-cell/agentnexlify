"""Shared imports and helpers for scheduled_jobs sub-modules."""
import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import (
    build_unsubscribe_url,
    render_template,
    send_email,
)
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background
from backend.services.automation.templates import (
    _REMINDER_EXTRAS,
    _REBOOK_INTERVALS,
    _AFTERCARE_TEMPLATES,
    _ONBOARDING_STEPS,
)
from backend.services.automation.trigger import BATCH_LIMIT, trigger_sequence

logger = logging.getLogger(__name__)


def _get_reminder_extras(business_type: str, notes: str) -> list[str]:
    """Return business-type-aware items to bring/prepare for an appointment."""
    extras = _REMINDER_EXTRAS.get(business_type, [])
    # Check if notes mention a specific service that needs extra instructions
    notes_lower = notes.lower()
    if business_type == "dental":
        if any(kw in notes_lower for kw in ["root canal", "surgery", "extraction"]):
            extras = extras + ["Arrange a ride home (sedation may be used)"]
        if "cleaning" in notes_lower or "checkup" in notes_lower:
            extras = extras + ["Floss before your visit"]
    return extras
