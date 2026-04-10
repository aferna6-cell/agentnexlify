"""Activity logging service — fire-and-forget, never raises."""


import logging
from typing import Any

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


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
