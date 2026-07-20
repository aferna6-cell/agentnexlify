"""Tenant activity-log CSV export (enterprise-audit item 7).

One tenant-scoped endpoint that streams the tenant's activity_log as CSV —
the cheap audit-trail checkbox every enterprise-suite buyer expects. Phone
numbers inside metadata are masked with the same rule the activity feed uses,
so the export never widens what the dashboard already shows.
"""

import csv
import io
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.activity import _mask_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])

_PAGE_SIZE = 1000
_MAX_ROWS = 50_000
_CSV_COLUMNS = ["created_at", "activity_type", "description", "lead_id", "metadata"]


def _mask_metadata(meta: dict) -> dict:
    for key in ("caller", "from_phone", "phone"):
        value = meta.get(key)
        if isinstance(value, str) and value:
            meta[key] = _mask_phone(value)
    return meta


def _fetch_rows(db, tenant_id: str, since: str | None, until: str | None) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while len(rows) < _MAX_ROWS:
        query = (
            db.table("activity_log")
            .select("created_at, activity_type, description, lead_id, metadata")
            .eq("tenant_id", tenant_id)
        )
        if since:
            query = query.gte("created_at", since)
        if until:
            query = query.lte("created_at", until)
        page = (
            query.order("created_at", desc=True)
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        ).data or []
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows[:_MAX_ROWS]


def _validate_iso(value: str | None, name: str) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{name} must be an ISO timestamp")
    return value


def render_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        meta = row.get("metadata") or {}
        if isinstance(meta, dict):
            meta = _mask_metadata(dict(meta))
        writer.writerow(
            {
                "created_at": row.get("created_at") or "",
                "activity_type": row.get("activity_type") or "",
                "description": row.get("description") or "",
                "lead_id": row.get("lead_id") or "",
                "metadata": json.dumps(meta, default=str, sort_keys=True),
            }
        )
    return buffer.getvalue()


@router.get("/export")
async def export_activity(
    claims: dict = Depends(_get_current_tenant),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
):
    """Stream the tenant's activity log as a CSV download."""
    tenant_id = claims["tenant_id"]
    since = _validate_iso(since, "since")
    until = _validate_iso(until, "until")
    db = get_service_supabase()
    try:
        rows = _fetch_rows(db, tenant_id, since, until)
    except Exception:
        logger.warning(
            "activity export failed tenant=%s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=502, detail="Activity export failed")

    filename = f"activity-{datetime.utcnow().date().isoformat()}.csv"
    return StreamingResponse(
        iter([render_csv(rows)]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
