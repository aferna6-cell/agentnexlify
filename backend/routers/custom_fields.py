"""Custom lead fields — per-tenant configurable attributes.

Lets businesses define custom fields (roof type, budget range, etc.)
that appear in lead capture, detail drawer, and filters.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/custom-fields", tags=["custom-fields"])


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Field Definition CRUD ---


class FieldCreate(BaseModel):
    field_name: str = Field(..., max_length=50)
    field_type: str = Field(default="text", pattern="^(text|number|dropdown|date|checkbox)$")
    options: list[str] = Field(default_factory=list)
    is_required: bool = False


class FieldUpdate(BaseModel):
    field_name: str | None = Field(None, max_length=50)
    options: list[str] | None = None
    is_required: bool | None = None
    sort_order: int | None = None


@router.get("/{tenant_id}")
async def list_custom_fields(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all custom field definitions for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("custom_field_definitions")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("sort_order")
        .execute()
    )
    return {"fields": result.data or []}


@router.post("/{tenant_id}")
async def create_custom_field(
    tenant_id: str,
    req: FieldCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new custom field definition."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Check for duplicate field name
    existing = (
        db.table("custom_field_definitions")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("field_name", req.field_name.strip())
        .limit(1)
        .execute()
    )
    if existing.count and existing.count > 0:
        raise HTTPException(status_code=409, detail=f"Field '{req.field_name}' already exists")

    # Get next sort_order
    count_result = (
        db.table("custom_field_definitions")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    next_order = (count_result.count or 0)

    data = {
        "tenant_id": tenant_id,
        "field_name": req.field_name.strip(),
        "field_type": req.field_type,
        "options": req.options,
        "is_required": req.is_required,
        "sort_order": next_order,
    }

    result = db.table("custom_field_definitions").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create field")
    return result.data[0]


@router.put("/{tenant_id}/{field_id}")
async def update_custom_field(
    tenant_id: str,
    field_id: str,
    req: FieldUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a custom field definition."""
    _verify_tenant(claims, tenant_id)

    updates = {}
    if req.field_name is not None:
        updates["field_name"] = req.field_name.strip()
    if req.options is not None:
        updates["options"] = req.options
    if req.is_required is not None:
        updates["is_required"] = req.is_required
    if req.sort_order is not None:
        updates["sort_order"] = req.sort_order

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    result = (
        db.table("custom_field_definitions")
        .update(updates)
        .eq("id", field_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Field not found")
    return result.data[0]


@router.delete("/{tenant_id}/{field_id}")
async def delete_custom_field(
    tenant_id: str,
    field_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a custom field definition."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    db.table("custom_field_definitions").delete().eq("id", field_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}


# --- Lead Custom Field Values ---


class SetCustomFieldValue(BaseModel):
    values: dict[str, str | int | bool | None]


@router.put("/{tenant_id}/lead/{lead_id}")
async def set_lead_custom_fields(
    tenant_id: str,
    lead_id: str,
    req: SetCustomFieldValue,
    claims: dict = Depends(_get_current_tenant),
):
    """Set custom field values on a lead."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Get current custom_fields
    lead = (
        db.table("leads")
        .select("custom_fields")
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    current = lead.data[0].get("custom_fields") or {}
    current.update(req.values)

    # Remove None values (unset)
    current = {k: v for k, v in current.items() if v is not None}

    result = (
        db.table("leads")
        .update({"custom_fields": current})
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update custom fields")
    return {"custom_fields": current}


@router.get("/{tenant_id}/lead/{lead_id}")
async def get_lead_custom_fields(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get custom field values for a lead."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    lead = (
        db.table("leads")
        .select("custom_fields")
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    return {"custom_fields": lead.data[0].get("custom_fields") or {}}
