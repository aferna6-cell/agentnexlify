"""Audit + recovery for destructive changes to customer/financial records.

Council finding #7: the platform must never quietly destroy or auto-edit a
customer or financial record. AI-initiated changes propose; a human approves.
And when a human DOES take a destructive action (e.g. merging two duplicate
leads, which deletes one row), the deleted data must be recoverable.

This module is the recovery half. It captures a full snapshot of a row before
it is destroyed and stashes it in the existing ``activity_log.metadata`` JSONB
(no new table needed). ``find_deleted_snapshot`` reads it back so the row can
be restored. ``leads`` uses ``client_id``; everything here is tenant-scoped via
the caller's ``log_activity`` / ``tenant_*`` helpers.
"""

from typing import Any

# Marker stored in activity_log.metadata so a destructive change is findable.
AUDIT_KEY = "destructive_snapshot"


def destructive_snapshot(table: str, row: dict, action: str, related_id: str | None = None) -> dict:
    """Build the activity_log.metadata payload that makes ``row`` recoverable.

    ``row`` is the full record as it existed immediately before deletion/edit.
    The payload is plain JSON so it survives a Supabase JSONB round-trip.
    """
    return {
        AUDIT_KEY: {
            "table": table,
            "action": action,
            "deleted_id": row.get("id"),
            "related_id": related_id,
            "row": dict(row),
        }
    }


def extract_snapshot(metadata: Any) -> dict | None:
    """Return the snapshot dict from an activity_log.metadata value, or None."""
    if not isinstance(metadata, dict):
        return None
    snap = metadata.get(AUDIT_KEY)
    return snap if isinstance(snap, dict) else None


def find_deleted_snapshot(db: Any, tenant_id: str, deleted_id: str) -> dict | None:
    """Find the most recent recoverable snapshot for a deleted record.

    Reads activity_log for this tenant and returns the snapshot whose
    ``deleted_id`` matches. Returns None if nothing recoverable is on file.
    Fails soft (returns None) so a recovery lookup never raises into a caller.
    """
    if not deleted_id:
        return None
    try:
        res = (
            db.table("activity_log")
            .select("metadata, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        rows = res.data or []
    except Exception:
        return None

    for entry in rows:
        snap = extract_snapshot(entry.get("metadata"))
        if snap and snap.get("deleted_id") == deleted_id:
            return snap
    return None
