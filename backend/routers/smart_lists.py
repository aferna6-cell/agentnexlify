"""Smart Lists — dynamic lead segments with filter-based queries and CSV export."""

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/smart-lists", tags=["smart-lists"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SmartListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    filter_json: dict = Field(default_factory=dict)


class SmartListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    filter_json: dict | None = None


# ---------------------------------------------------------------------------
# Filter engine
# ---------------------------------------------------------------------------

def _apply_filters(query, filters: dict):
    """Translate filter_json rules into Supabase PostgREST query chains.

    Supported filter keys:
        status          — list[str] → IN filter
        lead_temperature — str → exact match
        min_score       — int → lead_score >= value
        max_score       — int → lead_score <= value
        tags_include    — list[str] → array contains
        assigned_to     — str → exact match
        created_after   — str (ISO date) → created_at >= date
        created_before  — str (ISO date) → created_at <= date
        has_email       — bool → email IS NOT NULL
        has_phone       — bool → phone IS NOT NULL
        search          — str → name/email/phone ILIKE
    """
    if not filters:
        return query

    # status — IN filter (list of values)
    status_filter = filters.get("status")
    if status_filter:
        if isinstance(status_filter, list) and len(status_filter) > 0:
            query = query.in_("status", status_filter)
        elif isinstance(status_filter, str):
            query = query.eq("status", status_filter)

    # lead_temperature — exact match
    temp_filter = filters.get("lead_temperature")
    if temp_filter:
        if isinstance(temp_filter, str):
            query = query.eq("lead_temperature", temp_filter)
        elif isinstance(temp_filter, list) and len(temp_filter) > 0:
            query = query.in_("lead_temperature", temp_filter)

    # min_score — lead_score >= value
    min_score = filters.get("min_score")
    if min_score is not None:
        query = query.gte("lead_score", int(min_score))

    # max_score — lead_score <= value
    max_score = filters.get("max_score")
    if max_score is not None:
        query = query.lte("lead_score", int(max_score))

    # tags_include — array contains (uses cs = contains)
    tags_include = filters.get("tags_include")
    if tags_include and isinstance(tags_include, list) and len(tags_include) > 0:
        query = query.contains("tags", tags_include)

    # assigned_to — exact match
    assigned_to = filters.get("assigned_to")
    if assigned_to and isinstance(assigned_to, str):
        query = query.eq("assigned_to", assigned_to)

    # created_after — created_at >= date
    created_after = filters.get("created_after")
    if created_after and isinstance(created_after, str):
        query = query.gte("created_at", created_after)

    # created_before — created_at <= date
    created_before = filters.get("created_before")
    if created_before and isinstance(created_before, str):
        query = query.lte("created_at", created_before)

    # has_email — email IS NOT NULL
    if filters.get("has_email") is True:
        query = query.not_.is_("email", "null")

    # has_phone — phone IS NOT NULL
    if filters.get("has_phone") is True:
        query = query.not_.is_("phone", "null")

    # search — ILIKE on name, email, phone (uses or_ filter)
    search = filters.get("search")
    if search and isinstance(search, str) and search.strip():
        term = search.strip()
        query = query.or_(
            f"name.ilike.%{term}%,email.ilike.%{term}%,phone.ilike.%{term}%"
        )

    return query


def _execute_smart_list_query(tenant_id: str, filter_json: dict, db, select_cols: str = "*", count_only: bool = False):
    """Build and execute a leads query for a smart list's filters.

    Args:
        tenant_id: The tenant ID (used as client_id for leads table).
        filter_json: The filter rules from the smart list.
        db: Supabase client instance.
        select_cols: Columns to select.
        count_only: If True, only return count (no data).

    Returns:
        A tuple of (data_list, count).
    """
    if count_only:
        query = db.table("leads").select("id", count="exact").eq("client_id", tenant_id)
    else:
        query = db.table("leads").select(select_cols, count="exact").eq("client_id", tenant_id)

    query = _apply_filters(query, filter_json)

    if not count_only:
        query = query.order("created_at", desc=True)

    result = query.execute()
    data = result.data or []
    count = result.count if result.count is not None else len(data)
    return data, count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}")
async def list_smart_lists(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all smart lists for a tenant, ordered by creation date."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("smart_lists")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list smart lists for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load smart lists")

    return {"smart_lists": result.data or []}


@router.post("/{tenant_id}", status_code=201)
async def create_smart_list(
    tenant_id: str,
    req: SmartListCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new smart list with a name and filter definition."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Compute initial cached lead count
    cached_count = 0
    try:
        _, cached_count = _execute_smart_list_query(tenant_id, req.filter_json, db, count_only=True)
    except Exception:
        logger.warning("Could not compute initial lead count for new smart list, tenant %s", tenant_id, exc_info=True)

    now = datetime.now(timezone.utc).isoformat()
    data = {
        "tenant_id": tenant_id,
        "name": req.name,
        "description": req.description,
        "filter_json": req.filter_json,
        "cached_lead_count": cached_count,
        "last_refreshed_at": now,
        "is_default": False,
    }

    try:
        result = db.table("smart_lists").insert(data).execute()
    except Exception:
        logger.exception("Failed to create smart list for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create smart list")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create smart list")

    return result.data[0]


@router.put("/{tenant_id}/{list_id}")
async def update_smart_list(
    tenant_id: str,
    list_id: str,
    req: SmartListUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a smart list's name, description, or filter definition."""
    _verify_tenant(claims, tenant_id)

    updates: dict = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.filter_json is not None:
        updates["filter_json"] = req.filter_json

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_supabase()

    # If filter changed, refresh the cached count
    if req.filter_json is not None:
        try:
            _, new_count = _execute_smart_list_query(tenant_id, req.filter_json, db, count_only=True)
            updates["cached_lead_count"] = new_count
            updates["last_refreshed_at"] = updates["updated_at"]
        except Exception:
            logger.warning("Could not refresh lead count during smart list update, list %s", list_id, exc_info=True)

    try:
        result = (
            db.table("smart_lists")
            .update(updates)
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update smart list %s for tenant %s", list_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update smart list")

    if not result.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    return result.data[0]


@router.delete("/{tenant_id}/{list_id}")
async def delete_smart_list(
    tenant_id: str,
    list_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a smart list."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Prevent deletion of default lists
    try:
        existing = (
            db.table("smart_lists")
            .select("is_default")
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch smart list %s before delete", list_id)
        raise HTTPException(status_code=500, detail="Failed to fetch smart list")

    if not existing.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    if existing.data[0].get("is_default"):
        raise HTTPException(status_code=400, detail="Cannot delete a default smart list")

    try:
        db.table("smart_lists").delete().eq("id", list_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to delete smart list %s for tenant %s", list_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete smart list")

    return {"deleted": True}


@router.get("/{tenant_id}/{list_id}/leads")
async def get_smart_list_leads(
    tenant_id: str,
    list_id: str,
    claims: dict = Depends(_get_current_tenant),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Execute the smart list's filter and return matching leads with pagination."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch the smart list to get its filter_json
    try:
        sl_result = (
            db.table("smart_lists")
            .select("id, name, filter_json")
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch smart list %s for leads query", list_id)
        raise HTTPException(status_code=500, detail="Failed to fetch smart list")

    if not sl_result.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    smart_list = sl_result.data[0]
    filter_json = smart_list.get("filter_json") or {}

    # Execute the filtered leads query with pagination
    try:
        select_cols = (
            "id, name, email, phone, status, lead_score, lead_temperature, "
            "areas_of_interest, tags, assigned_to, deal_value, expected_close_date, "
            "created_at, updated_at"
        )
        query = (
            db.table("leads")
            .select(select_cols, count="exact")
            .eq("client_id", tenant_id)
        )
        query = _apply_filters(query, filter_json)
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
    except Exception:
        logger.exception("Failed to execute smart list %s leads query for tenant %s", list_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query leads")

    leads = result.data or []
    total = result.count if result.count is not None else len(leads)

    return {
        "smart_list": smart_list.get("name"),
        "leads": leads,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/{tenant_id}/{list_id}/refresh")
async def refresh_smart_list(
    tenant_id: str,
    list_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Refresh the cached lead count for a smart list."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch the smart list
    try:
        sl_result = (
            db.table("smart_lists")
            .select("id, filter_json")
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch smart list %s for refresh", list_id)
        raise HTTPException(status_code=500, detail="Failed to fetch smart list")

    if not sl_result.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    filter_json = sl_result.data[0].get("filter_json") or {}

    # Count matching leads
    try:
        _, new_count = _execute_smart_list_query(tenant_id, filter_json, db, count_only=True)
    except Exception:
        logger.exception("Failed to count leads for smart list %s refresh", list_id)
        raise HTTPException(status_code=500, detail="Failed to count matching leads")

    # Update cached count
    now = datetime.now(timezone.utc).isoformat()
    try:
        update_result = (
            db.table("smart_lists")
            .update({
                "cached_lead_count": new_count,
                "last_refreshed_at": now,
                "updated_at": now,
            })
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update cached count for smart list %s", list_id)
        raise HTTPException(status_code=500, detail="Failed to update cached count")

    if not update_result.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    return update_result.data[0]


@router.get("/{tenant_id}/{list_id}/export")
async def export_smart_list(
    tenant_id: str,
    list_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Export matching leads as a CSV file download."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch the smart list
    try:
        sl_result = (
            db.table("smart_lists")
            .select("id, name, filter_json")
            .eq("id", list_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch smart list %s for export", list_id)
        raise HTTPException(status_code=500, detail="Failed to fetch smart list")

    if not sl_result.data:
        raise HTTPException(status_code=404, detail="Smart list not found")

    smart_list = sl_result.data[0]
    filter_json = smart_list.get("filter_json") or {}
    list_name = smart_list.get("name", "smart-list")

    # Fetch all matching leads (no pagination for export, but cap at 5000 to prevent abuse)
    try:
        select_cols = (
            "id, name, email, phone, status, lead_score, lead_temperature, "
            "areas_of_interest, tags, assigned_to, deal_value, expected_close_date, "
            "created_at, updated_at"
        )
        query = (
            db.table("leads")
            .select(select_cols)
            .eq("client_id", tenant_id)
        )
        query = _apply_filters(query, filter_json)
        query = query.order("created_at", desc=True)
        query = query.limit(5000)
        result = query.execute()
    except Exception:
        logger.exception("Failed to query leads for smart list %s export", list_id)
        raise HTTPException(status_code=500, detail="Failed to query leads for export")

    leads = result.data or []

    # Build CSV in memory
    csv_columns = [
        "id", "name", "email", "phone", "status", "lead_score",
        "lead_temperature", "areas_of_interest", "tags", "assigned_to",
        "deal_value", "expected_close_date", "created_at", "updated_at",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=csv_columns, extrasaction="ignore")
    writer.writeheader()

    for lead in leads:
        # Convert tags list to a semicolon-separated string for CSV readability
        tags = lead.get("tags")
        if isinstance(tags, list):
            lead["tags"] = "; ".join(str(t) for t in tags)
        writer.writerow(lead)

    csv_content = output.getvalue()
    output.close()

    # Sanitize list name for filename
    safe_name = "".join(c if c.isalnum() or c in ("-", "_", " ") else "" for c in list_name).strip().replace(" ", "-")
    if not safe_name:
        safe_name = "smart-list"
    filename = f"{safe_name}-leads-export.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
