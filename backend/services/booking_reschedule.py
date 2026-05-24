"""Reschedule URL helpers — signed HMAC tokens for self-serve reschedule links."""


import hashlib
import hmac
from datetime import datetime, timezone

from backend.config import settings

_RESCHEDULE_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60


def _generate_reschedule_token(appointment_id: str) -> str:
    """Generate an expiring HMAC token for appointment reschedule links."""
    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload = f"reschedule:{appointment_id}:{issued_at}"
    signature = hmac.new(
        settings.api_secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{issued_at}.{signature}"


def build_reschedule_url(appointment_id: str, business_slug: str = "") -> str:
    """Build a public reschedule URL with a signed HMAC token."""
    from backend.services import booking as _b

    token = _b._generate_reschedule_token(appointment_id)
    base_url = settings.api_url
    return f"{base_url}/api/v1/book/reschedule/{appointment_id}?token={token}"
