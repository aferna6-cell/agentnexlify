"""Bulk update helpers for leads.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)


def _build_update_payload(
    *,
    status: str | None,
    assigned_to: str | None,
) -> dict:
    """Build the base update payload (status + assigned_to) for a single lead.

    `assigned_to=""` is normalized to `None` so the column gets cleared rather
    than written as an empty string.
    """
    payload: dict = {}
    if status:
        payload["status"] = status
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to if assigned_to else None
    return payload


def _merge_tags(
    db: Any, tenant_id: str, lead_id: str, tags_to_add: list[str]
) -> list[str] | None:
    """Read existing tags for a lead and union them with `tags_to_add`.

    Returns the merged tag list, or None when the lead row cannot be found
    (caller should skip the tag update in that case).
    """
    existing = (
        tenant_select(db, "leads", tenant_id, "tags")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return None
    current = existing.data[0].get("tags") or []
    return list(set(current + tags_to_add))


def apply_bulk_lead_updates(
    db: Any,
    tenant_id: str,
    *,
    lead_ids: list[str],
    status: str | None = None,
    assigned_to: str | None = None,
    tags_add: list[str] | None = None,
) -> tuple[int, list[str]]:
    """Apply the same set of column updates to many leads.

    Returns `(updated_count, failed_ids)`. Each lead is its own transaction;
    one failure does not abort the rest. Errors are logged at WARNING.
    """
    updated = 0
    failed: list[str] = []

    for lead_id in lead_ids:
        try:
            payload = _build_update_payload(
                status=status, assigned_to=assigned_to
            )
            if tags_add:
                merged = _merge_tags(db, tenant_id, lead_id, tags_add)
                if merged is not None:
                    payload["tags"] = merged

            if not payload:
                continue

            result = (
                tenant_update(db, "leads", tenant_id, payload)
                .eq("id", lead_id)
                .execute()
            )
            if result.data:
                updated += 1
            else:
                failed.append(lead_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Bulk update failed for lead %s: %s", lead_id, exc
            )
            failed.append(lead_id)

    return updated, failed
