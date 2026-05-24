"""Public booking page — pure logic.

Tenant/slug lookup, widget color, slot availability, reschedule-token HMAC.
Router stays thin: auth + HTTP + Pydantic only.
"""

import hashlib
import hmac
import logging
from datetime import date, datetime, timezone
from typing import Any

from backend.config import settings
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

RESCHEDULE_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_WIDGET_COLOR = "#00BFFF"


class BookingTenantNotFound(Exception):
    """Raised when no tenant matches the given business_slug."""


class BookingTenantLookupFailed(Exception):
    """Raised when the slug lookup itself errors (DB unavailable, etc.)."""


def lookup_tenant_by_slug(db: Any, slug: str) -> dict:
    """Return tenant row for the given business_slug.

    Raises:
        BookingTenantNotFound: slug has no matching tenant.
        BookingTenantLookupFailed: DB error during lookup.
    """
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, owner_email, plan")
            .eq("business_slug", slug)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("DB error looking up tenant by slug %s", slug)
        raise BookingTenantLookupFailed(str(exc)) from exc

    if not result.data:
        raise BookingTenantNotFound(slug)

    return result.data[0]


def fetch_widget_color(db: Any, tenant_id: str) -> str:
    """Return the tenant's primary branding color, or DEFAULT_WIDGET_COLOR."""
    try:
        result = (
            tenant_table(db, "widget_configs", tenant_id)
            .select("primary_color")
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("primary_color"):
            return result.data[0]["primary_color"]
    except Exception:
        logger.warning("Could not fetch widget color for tenant %s", tenant_id, exc_info=True)
    return DEFAULT_WIDGET_COLOR


def slot_available(db: Any, tenant_id: str, start_iso: str, end_iso: str) -> bool:
    """Return True if the requested slot is open (no overlapping confirmed appt).

    Fails safe: any DB error returns False to avoid double-booking.
    """
    try:
        result = (
            tenant_table(db, "appointments", tenant_id)
            .select("id")
            .eq("status", "confirmed")
            .lt("start_time", end_iso)
            .gt("end_time", start_iso)
            .limit(1)
            .execute()
        )
        return not result.data
    except Exception:
        logger.exception("DB error checking slot availability for tenant %s", tenant_id)
        return False


def verify_reschedule_token(appointment_id: str, token: str) -> bool:
    """Verify HMAC reschedule token. Supports legacy (no timestamp) + current (timestamp.sig)."""
    if "." not in token:
        allow_legacy = getattr(settings, "allow_legacy_reschedule_tokens", False)
        if not allow_legacy:
            return False
        expected = hmac.new(
            settings.api_secret_key.encode(),
            f"reschedule:{appointment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, token)

    issued_at_raw, signature = token.split(".", 1)
    try:
        issued_at = int(issued_at_raw)
    except ValueError:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    if issued_at > now or now - issued_at > RESCHEDULE_TOKEN_TTL_SECONDS:
        return False

    payload = f"reschedule:{appointment_id}:{issued_at}"
    expected = hmac.new(
        settings.api_secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def format_service_note(db: Any, tenant_id: str, service_type_id: str | None) -> str:
    """Look up service type name and return the appointment note string."""
    default = "Booked via public booking page"
    if not service_type_id:
        return default
    try:
        st_row = (
            tenant_table(db, "service_types", tenant_id)
            .select("name, duration_minutes")
            .eq("id", service_type_id)
            .limit(1)
            .execute()
        )
        if st_row.data:
            name = st_row.data[0]["name"]
            duration = st_row.data[0]["duration_minutes"]
            return f"Service: {name} ({duration} min) — Booked via public booking page"
    except Exception:
        logger.warning("Could not look up service type %s", service_type_id, exc_info=True)
    return default


def fetch_active_service_types(db: Any, tenant_id: str) -> list[dict]:
    """Return active service types for the tenant, sorted by sort_order."""
    try:
        result = (
            tenant_table(db, "service_types", tenant_id)
            .select("id, name, duration_minutes, description, price")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        return result.data or []
    except Exception:
        logger.warning("Could not fetch service types for tenant %s", tenant_id, exc_info=True)
        return []


def parse_start_date(date_str: str) -> date:
    """Parse YYYY-MM-DD; raises ValueError on bad input."""
    return date.fromisoformat(date_str)
