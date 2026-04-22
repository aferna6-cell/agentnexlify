"""Activity logging service — fire-and-forget, never raises."""

import logging
import re
from datetime import datetime
from typing import Any

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


def _mask_phone(phone: str) -> str:
    """Mask phone to last-4 visible: +1234****7890.

    Examples:
        +12345557890  ->  +1234****7890
        12345557890   ->  1234****7890
        5557890       ->  ***7890  (short number fallback)
    """
    stripped = phone.strip()
    prefix = "+" if stripped.startswith("+") else ""
    digits = re.sub(r"\D", "", stripped)  # pure digits only

    if len(digits) >= 8:
        # Show first (len - 8) digits, mask 4, show last 4
        # e.g. 12345557890 (11 digits): show 3 + **** + 4 = "123****7890"
        # But spec wants +1234****7890 from +12345557890:
        # digits = 12345557890 (11 digits), show first 7-4=... no.
        # Spec: +12345557890 -> +1234****7890: prefix=+, show 4 digits, ****, last 4.
        # Rule: show (len(digits) - 8) prefix digits + **** + last 4
        # 11 digits: show 11-8=3 -> +123****7890 — but spec says +1234****7890 (4 shown).
        # Recount: +12345557890 has digits=12345557890 (11). Spec output: +1234****7890
        # That's 4 visible + **** + 4 = 12 total digits shown. But input is 11.
        # Actually spec says "last 4 visible" for the masked middle, keep start up to len-8+1.
        # Simplest: always show first 4 digits of the number, then ****, then last 4.
        # Only apply when total digits >= 9 (otherwise overlap).
        visible_start = digits[:-8] if len(digits) > 8 else ""
        # Ensure at least 4 visible start chars when number is long enough
        if len(digits) >= 9 and len(visible_start) < 4:
            visible_start = digits[:4]
        masked = prefix + visible_start + "****" + digits[-4:]
        return masked
    # Short number fallback — mask all but last 4
    if len(digits) > 4:
        return prefix + "***" + digits[-4:]
    return prefix + digits


def log_activity(
    tenant_id: str,
    activity_type: str,
    description: str,
    lead_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Insert a row into activity_log. Silently swallows errors."""
    try:
        db = get_service_supabase()
        row: dict[str, Any] = {
            "tenant_id": tenant_id,
            "activity_type": activity_type,
            "description": description,
            "metadata": metadata or {},
        }
        if lead_id:
            row["lead_id"] = lead_id
        db.table("activity_log").insert(row).execute()
    except Exception:
        logger.warning(
            "Failed to log activity type=%s tenant=%s",
            activity_type,
            tenant_id,
            exc_info=True,
        )


def get_activity_events(
    tenant_id: str,
    since: datetime | None = None,
    type_filter: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Return recent activity_log rows for a tenant, phone numbers masked.

    Args:
        tenant_id: Tenant UUID string.
        since: Only return events after this UTC datetime. Defaults to no filter.
        type_filter: Match ``activity_type`` column exactly when provided.
        limit: Maximum rows returned. Defaults to 5.

    Returns:
        List of dicts with keys: id, tenant_id, activity_type, description,
        metadata (phone masked), lead_id, created_at.
    """
    try:
        db = get_service_supabase()
        query = (
            db.table("activity_log")
            .select(
                "id, tenant_id, activity_type, description, metadata, lead_id, created_at"
            )
            .eq("tenant_id", tenant_id)
        )
        if since is not None:
            query = query.gte("created_at", since.isoformat())
        if type_filter is not None:
            query = query.eq("activity_type", type_filter)
        result = query.order("created_at", desc=True).limit(limit).execute()
        rows = result.data or []

        # Mask phone numbers in metadata
        for row in rows:
            meta = row.get("metadata") or {}
            for key in ("caller", "from_phone", "phone"):
                if key in meta and isinstance(meta[key], str) and meta[key]:
                    meta[key] = _mask_phone(meta[key])
            row["metadata"] = meta

        return rows
    except Exception:
        logger.warning(
            "Failed to get activity events tenant=%s", tenant_id, exc_info=True
        )
        return []


def get_activity_totals(
    tenant_id: str,
    since: datetime | None = None,
) -> dict:
    """Return aggregate totals for a tenant's activity_log.

    Phase 2: returns events_count + dollars_this_month + hours_this_week.

    Args:
        tenant_id: Tenant UUID string.
        since: Only count events after this UTC datetime (for events_count).

    Returns:
        Dict with keys: events_count (int), dollars_this_month (float),
        hours_this_week (float).
    """
    from backend.services.attribution_service import (
        compute_dollars_this_month,
        compute_hours_this_week,
    )

    try:
        db = get_service_supabase()
        query = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
        )
        if since is not None:
            query = query.gte("created_at", since.isoformat())
        result = query.execute()
        count = result.count if result.count is not None else len(result.data or [])
    except Exception:
        logger.warning(
            "Failed to get activity totals tenant=%s", tenant_id, exc_info=True
        )
        count = 0

    dollars = compute_dollars_this_month(tenant_id)
    hours = compute_hours_this_week(tenant_id)

    return {
        "events_count": count,
        "dollars_this_month": dollars,
        "hours_this_week": hours,
    }
