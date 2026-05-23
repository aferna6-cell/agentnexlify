"""Duplicate detection + merge helpers for the leads router.

Pulled out of `find_duplicate_leads` and `merge_leads` so the router stays
focused on HTTP auth and response shape. Functions here own the dedup
group logic, field fill-in, tag union, and cross-table reassignment.

DB helpers accept `db: Any` so test patches at
`backend.routers.leads.get_service_supabase` still apply.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_delete, tenant_select, tenant_update

logger = logging.getLogger(__name__)


FILLABLE_FIELDS: list[str] = [
    "name", "email", "phone", "lead_type", "areas_of_interest",
    "timeline", "budget", "conversation_summary", "next_steps",
]


def fetch_duplicate_groups(db: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Return groups of 2+ leads sharing email or phone.

    Each entry: `{match_field, match_value, leads}`. Groups deduped by
    member-id tuple so an email match and a phone match for the same set
    don't double-count.
    """
    result = tenant_select(
        db,
        "leads",
        tenant_id,
        "id, name, email, phone, status, lead_score, created_at",
    ).execute()
    leads = result.data or []

    email_groups: dict[str, list] = {}
    phone_groups: dict[str, list] = {}
    for lead in leads:
        email = (lead.get("email") or "").strip().lower()
        phone = (lead.get("phone") or "").strip()
        if email:
            email_groups.setdefault(email, []).append(lead)
        if phone:
            phone_groups.setdefault(phone, []).append(lead)

    duplicate_sets: list[dict[str, Any]] = []
    seen_ids: set[tuple] = set()
    for key, group in {**email_groups, **phone_groups}.items():
        if len(group) < 2:
            continue
        ids = tuple(sorted(l["id"] for l in group))
        if ids in seen_ids:
            continue
        seen_ids.add(ids)
        duplicate_sets.append({
            "match_field": "email" if "@" in key else "phone",
            "match_value": key,
            "leads": group,
        })

    return duplicate_sets


def compute_merge_updates(
    keep: dict[str, Any], merge: dict[str, Any]
) -> dict[str, Any]:
    """Build the update dict for the keep-record.

    Fills missing scalar fields from merge, unions tag arrays, and
    promotes the higher lead_score.
    """
    updates: dict[str, Any] = {}
    for field in FILLABLE_FIELDS:
        if not keep.get(field) and merge.get(field):
            updates[field] = merge[field]

    keep_tags = keep.get("tags") or []
    merge_tags = merge.get("tags") or []
    combined_tags = list(dict.fromkeys(keep_tags + merge_tags))
    if combined_tags != keep_tags:
        updates["tags"] = combined_tags

    if (merge.get("lead_score") or 0) > (keep.get("lead_score") or 0):
        updates["lead_score"] = merge["lead_score"]

    return updates


def reassign_lead_references(
    db: Any, tenant_id: str, *, from_id: str, to_id: str
) -> None:
    """Move appointments, activity_log, and client_notes from one lead to another.

    Per-table failures are logged but don't abort the merge.
    """
    for table in ("appointments", "activity_log", "client_notes"):
        try:
            tenant_update(db, table, tenant_id, {"lead_id": to_id}).eq(
                "lead_id", from_id
            ).execute()
        except Exception:
            logger.warning(
                "Failed to reassign %s during merge", table, exc_info=True
            )


def apply_lead_merge(
    db: Any, tenant_id: str, *, keep_id: str, merge_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Apply merge logic to two leads. Returns `(keep, merge, updates)`.

    Caller is responsible for raising HTTP 404 when records missing and
    logging the merge activity.
    """
    keep_result = tenant_select(db, "leads", tenant_id).eq("id", keep_id).limit(1).execute()
    merge_result = tenant_select(db, "leads", tenant_id).eq("id", merge_id).limit(1).execute()

    if not keep_result.data:
        raise LookupError("keep")
    if not merge_result.data:
        raise LookupError("merge")

    keep = keep_result.data[0]
    merge = merge_result.data[0]

    updates = compute_merge_updates(keep, merge)
    if updates:
        tenant_update(db, "leads", tenant_id, updates).eq("id", keep_id).execute()

    reassign_lead_references(db, tenant_id, from_id=merge_id, to_id=keep_id)
    tenant_delete(db, "leads", tenant_id).eq("id", merge_id).execute()

    return keep, merge, updates
