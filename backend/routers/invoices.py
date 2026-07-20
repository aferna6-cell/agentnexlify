"""Invoicing & Text-to-Pay — create, send, and track invoices with Stripe Payment Links.

Split per issue #473: this module keeps the Pydantic contracts, auth, and
route registration; the flow bodies live in services:

  - backend/services/invoice_helpers.py — totals, numbering, payment links, stats
  - backend/services/invoice_email.py   — email HTML rendering
  - backend/services/invoice_crud.py    — create/from-bid/list/get/update/delete/payments
  - backend/services/invoice_send.py    — single + bulk delivery flows

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant, require_role
from backend.services import invoice_crud, invoice_send
from backend.services.invoice_helpers import compute_invoice_stats
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class InvoiceItemModel(BaseModel):
    description: str = Field(..., max_length=500)
    quantity: float = Field(1.0, ge=0)
    unit_price: float = Field(0.0, ge=0)


class InvoiceCreate(BaseModel):
    items: list[InvoiceItemModel] = Field(default_factory=list)
    tax_rate: float = Field(0.0, ge=0, le=100)
    due_date: date | None = None
    lead_id: str | None = None
    bid_id: str | None = None
    notes: str | None = Field(None, max_length=5000)
    deposit_amount: float = Field(0.0, ge=0)
    is_recurring: bool = False
    recurrence_interval: str | None = Field(None, pattern="^(weekly|biweekly|monthly|quarterly)$")


class InvoiceUpdate(BaseModel):
    items: list[InvoiceItemModel] | None = None
    tax_rate: float | None = Field(None, ge=0, le=100)
    due_date: date | None = None
    lead_id: str | None = None
    notes: str | None = Field(None, max_length=5000)


class SendInvoiceRequest(BaseModel):
    method: str = Field(..., pattern="^(email|sms|both)$")


class MarkPaidRequest(BaseModel):
    payment_method: str | None = Field(None, max_length=100)


class RecordPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str | None = Field(None, max_length=100)


class ItemTemplateCreate(BaseModel):
    description: str = Field(..., max_length=500)
    unit_price: float = Field(0.0, ge=0)
    category: str | None = Field(None, max_length=100)


class ItemTemplateUpdate(BaseModel):
    description: str | None = Field(None, max_length=500)
    unit_price: float | None = Field(None, ge=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class BulkSendRequest(BaseModel):
    invoice_ids: list[str] = Field(..., max_length=50)
    channel: str = Field("email", pattern="^(email|sms|both)$")


# ---------------------------------------------------------------------------
# Endpoints
# IMPORTANT: Static sub-paths (/{tenant_id}/stats, /{tenant_id}/from-bid/{bid_id},
# /{tenant_id}/item-templates, /{tenant_id}/bulk-send) are registered BEFORE the
# dynamic /{tenant_id}/{invoice_id} route so FastAPI does not mistake the literal
# path segments for invoice IDs.
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/stats")
async def invoice_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Invoice summary statistics: outstanding balance, paid total, overdue count, avg days to pay."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("status, total, created_at, paid_at, sent_at")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice stats for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice stats")

    return compute_invoice_stats(result.data or [])


@router.post("/{tenant_id}/from-bid/{bid_id}", status_code=201)
async def create_invoice_from_bid(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create an invoice by copying items and amounts from an accepted bid."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.create_invoice_from_bid_flow(db, tenant_id, bid_id)


@router.get("/{tenant_id}")
async def list_invoices(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None, description="Filter by status"),
    lead_id: str | None = Query(None, description="Filter by lead"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List invoices for a tenant. Joins lead name for display."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.list_invoices_flow(db, tenant_id, status, lead_id, offset, limit)


@router.post("/{tenant_id}", status_code=201)
async def create_invoice(
    tenant_id: str,
    req: InvoiceCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new invoice. Auto-calculates subtotal, tax, and total."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.create_invoice_flow(db, tenant_id, req)


# ---------------------------------------------------------------------------
# Item Templates (Line Item Library)
# Must be before /{tenant_id}/{invoice_id} to avoid route shadowing
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Bulk send — static path, must precede /{tenant_id}/{invoice_id}
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/bulk-send")
async def bulk_send_invoices(
    tenant_id: str,
    req: BulkSendRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Send multiple invoices at once. Max 50 per request."""
    verify_tenant(claims, tenant_id)

    if not req.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided")
    if len(req.invoice_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 invoices per bulk send")

    db = get_service_supabase()
    return await invoice_send.bulk_send_flow(db, tenant_id, req.invoice_ids, req.channel)


# ---------------------------------------------------------------------------
# Single Invoice Operations
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/{invoice_id}")
async def get_invoice(
    tenant_id: str,
    invoice_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single invoice with lead details."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.get_invoice_flow(db, tenant_id, invoice_id)


@router.put("/{tenant_id}/{invoice_id}")
async def update_invoice(
    tenant_id: str,
    invoice_id: str,
    req: InvoiceUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update an invoice. Only allowed when status is 'draft'."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.update_invoice_flow(db, tenant_id, invoice_id, req)


@router.delete("/{tenant_id}/{invoice_id}")
async def delete_invoice(
    tenant_id: str,
    invoice_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete an invoice. Only allowed when status is 'draft'."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.delete_invoice_flow(db, tenant_id, invoice_id)


@router.post("/{tenant_id}/{invoice_id}/send")
async def send_invoice(
    tenant_id: str,
    invoice_id: str,
    req: SendInvoiceRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Send an invoice to the customer via email, SMS, or both.

    Creates a Stripe Payment Link if one does not yet exist, then dispatches
    via the requested channel(s). Updates status to 'sent'.
    """
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_send.send_invoice_flow(db, tenant_id, invoice_id, req.method)


@router.post("/{tenant_id}/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    tenant_id: str,
    invoice_id: str,
    req: MarkPaidRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Manually mark an invoice as paid."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.mark_invoice_paid_flow(db, tenant_id, invoice_id, req.payment_method)


@router.post("/{tenant_id}/{invoice_id}/record-payment")
async def record_partial_payment(
    tenant_id: str,
    invoice_id: str,
    req: RecordPaymentRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Record a partial payment against an invoice."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return await invoice_crud.record_partial_payment_flow(db, tenant_id, invoice_id, req.amount, req.payment_method)
