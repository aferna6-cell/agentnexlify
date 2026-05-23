"""Invoice item templates — reusable line items for invoice creation."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


class ItemTemplateCreate(BaseModel):
    description: str = Field(..., max_length=500)
    unit_price: float = Field(0.0, ge=0)
    category: str | None = Field(None, max_length=100)


class ItemTemplateUpdate(BaseModel):
    description: str | None = Field(None, max_length=500)
    unit_price: float | None = Field(None, ge=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool | None = None


@router.get("/{tenant_id}/item-templates")
async def list_item_templates(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all item templates for a tenant."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = (
        tenant_table(db, "invoice_item_templates", tenant_id)
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("category")
        .order("sort_order")
        .execute()
    )
    return result.data or []


@router.post("/{tenant_id}/item-templates")
async def create_item_template(
    tenant_id: str,
    req: ItemTemplateCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a reusable line item template."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = tenant_table(db, "invoice_item_templates", tenant_id).insert({
        "tenant_id": tenant_id,
        "description": req.description,
        "unit_price": float(req.unit_price),
        "category": req.category,
    }).execute()
    return result.data[0] if result.data else {}


@router.put("/{tenant_id}/item-templates/{template_id}")
async def update_item_template(
    tenant_id: str,
    template_id: str,
    req: ItemTemplateUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update an item template."""
    verify_tenant(claims, tenant_id)
    updates = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db = get_service_supabase()
    result = (
        tenant_table(db, "invoice_item_templates", tenant_id)
        .update(updates)
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return result.data[0]


@router.delete("/{tenant_id}/item-templates/{template_id}")
async def delete_item_template(
    tenant_id: str,
    template_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Soft-delete an item template."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = (
        tenant_table(db, "invoice_item_templates", tenant_id)
        .update({"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}
