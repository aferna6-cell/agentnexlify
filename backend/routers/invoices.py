"""Invoicing & Text-to-Pay — create, send, and track invoices with Stripe Payment Links."""

import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant, require_role
from backend.services.email_sender import send_email
from backend.services.invoice_calculations import compute_invoice_totals
from backend.services.invoice_email_template import build_invoice_email_html
from backend.services.invoice_numbering import get_next_invoice_number
from backend.services.invoice_payment_links import get_or_create_stripe_payment_link
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

# Re-export private aliases — preserved for any existing test patches and call sites.
_compute_invoice_totals = compute_invoice_totals
_get_next_invoice_number = get_next_invoice_number
_get_or_create_stripe_payment_link = get_or_create_stripe_payment_link
_build_invoice_email_html = build_invoice_email_html

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


# ---------------------------------------------------------------------------
# Helpers — extracted to backend.services.invoice_* modules
# ---------------------------------------------------------------------------
# `_compute_invoice_totals`, `_get_next_invoice_number`,
# `_get_or_create_stripe_payment_link`, and `_build_invoice_email_html` are
# re-exported above as aliases of the canonical service implementations.


# ---------------------------------------------------------------------------
# Endpoints
# IMPORTANT: Static sub-paths (/{tenant_id}/stats, /{tenant_id}/from-bid/{bid_id})
# are registered BEFORE the dynamic /{tenant_id}/{invoice_id} route so FastAPI
# does not mistake the literal path segments for invoice IDs.
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

    invoices = result.data or []

    total_outstanding = round(
        sum(float(i.get("total", 0)) for i in invoices if i.get("status") in ("sent", "viewed")),
        2,
    )
    total_paid = round(
        sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "paid"),
        2,
    )
    overdue_count = sum(1 for i in invoices if i.get("status") == "overdue")
    paid_count = sum(1 for i in invoices if i.get("status") == "paid")

    # Average days from sent_at to paid_at for paid invoices
    avg_days_to_payment: float | None = None
    days_list = []
    for inv in invoices:
        if inv.get("status") == "paid" and inv.get("sent_at") and inv.get("paid_at"):
            try:
                sent = datetime.fromisoformat(inv["sent_at"].replace("Z", "+00:00"))
                paid = datetime.fromisoformat(inv["paid_at"].replace("Z", "+00:00"))
                delta_days = (paid - sent).total_seconds() / 86400
                if delta_days >= 0:
                    days_list.append(delta_days)
            except Exception:
                logger.warning("Could not parse dates for invoice stats", exc_info=True)
    if days_list:
        avg_days_to_payment = round(sum(days_list) / len(days_list), 1)

    return {
        "total_outstanding": total_outstanding,
        "total_paid": total_paid,
        "overdue_count": overdue_count,
        "paid_count": paid_count,
        "total_invoices": len(invoices),
        "avg_days_to_payment": avg_days_to_payment,
    }


@router.post("/{tenant_id}/from-bid/{bid_id}", status_code=201)
async def create_invoice_from_bid(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create an invoice by copying items and amounts from an accepted bid."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Fetch the bid
    try:
        bid_result = (
            tenant_table(db, "bids", tenant_id)
            .select("*")
            .eq("id", bid_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch bid %s for invoice creation", bid_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid")

    if not bid_result.data:
        raise HTTPException(status_code=404, detail="Bid not found")

    bid = bid_result.data[0]

    # Only accepted bids can be converted to invoices
    if bid.get("status") != "accepted":
        raise HTTPException(
            status_code=400,
            detail=f"Bid status is '{bid.get('status')}' — only accepted bids can be converted to invoices",
        )

    # Prevent duplicate invoice creation from the same bid
    try:
        existing_invoice = (
            tenant_table(db, "invoices", tenant_id)
            .select("id, invoice_number")
            .eq("tenant_id", tenant_id)
            .eq("bid_id", bid_id)
            .limit(1)
            .execute()
        )
        if existing_invoice.data:
            raise HTTPException(
                status_code=409,
                detail=f"An invoice ({existing_invoice.data[0].get('invoice_number', '')}) already exists for this bid",
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning("Could not check for existing invoice from bid %s", bid_id, exc_info=True)

    bid_items_raw = bid.get("items_json") or []

    # Normalize bid items to invoice item format
    invoice_items = []
    for item in bid_items_raw:
        invoice_items.append({
            "description": item.get("description", ""),
            "quantity": item.get("quantity", 1),
            "unit_price": item.get("unit_price", 0),
        })

    subtotal, tax_amount, total = _compute_invoice_totals(invoice_items, 0.0)
    invoice_number = await _get_next_invoice_number(db, tenant_id)

    data = {
        "tenant_id": tenant_id,
        "bid_id": bid_id,
        "lead_id": bid.get("lead_id"),
        "invoice_number": invoice_number,
        "items_json": invoice_items,
        "subtotal": subtotal,
        "tax_rate": 0.0,
        "tax_amount": tax_amount,
        "total": total,
        "status": "draft",
        "notes": f"Created from bid: {bid.get('title', bid_id)}",
    }

    try:
        result = tenant_table(db, "invoices", tenant_id).insert(data).execute()
    except Exception:
        logger.exception("Failed to create invoice from bid %s for tenant %s", bid_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create invoice from bid")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create invoice from bid")
    return result.data[0]


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
    try:
        query = (
            tenant_table(db, "invoices", tenant_id)
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("status", status)
        if lead_id:
            query = query.eq("lead_id", lead_id)
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
    except Exception:
        logger.exception("Failed to list invoices for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list invoices")

    invoices = result.data or []

    # Enrich with lead names — collect unique lead IDs, batch query leads table
    lead_ids = list({inv["lead_id"] for inv in invoices if inv.get("lead_id")})
    lead_names: dict[str, str] = {}
    if lead_ids:
        try:
            leads_result = (
                tenant_table(db, "leads", tenant_id)
                .select("id, name")
                .in_("id", lead_ids)
                .eq("client_id", tenant_id)
                .execute()
            )
            for lead in (leads_result.data or []):
                lead_names[lead["id"]] = lead.get("name") or ""
        except Exception:
            logger.warning("Could not batch-fetch lead names for invoice list, tenant %s", tenant_id, exc_info=True)

    for inv in invoices:
        inv["lead_name"] = lead_names.get(inv.get("lead_id", ""), "")

    return {
        "invoices": invoices,
        "count": result.count or len(invoices),
        "offset": offset,
        "limit": limit,
    }


@router.post("/{tenant_id}", status_code=201)
async def create_invoice(
    tenant_id: str,
    req: InvoiceCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new invoice. Auto-calculates subtotal, tax, and total."""
    verify_tenant(claims, tenant_id)

    items = [item.model_dump() for item in req.items]
    subtotal, tax_amount, total = _compute_invoice_totals(items, req.tax_rate)

    if req.deposit_amount > total:
        raise HTTPException(status_code=400, detail="deposit_amount cannot exceed invoice total")

    db = get_service_supabase()
    invoice_number = await _get_next_invoice_number(db, tenant_id)

    data: dict = {
        "tenant_id": tenant_id,
        "invoice_number": invoice_number,
        "items_json": items,
        "subtotal": subtotal,
        "tax_rate": req.tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "status": "draft",
    }
    if req.due_date is not None:
        data["due_date"] = req.due_date.isoformat()
    if req.lead_id:
        data["lead_id"] = req.lead_id
    if req.bid_id:
        data["bid_id"] = req.bid_id
    if req.notes is not None:
        data["notes"] = req.notes
    if req.deposit_amount > 0:
        data["deposit_amount"] = req.deposit_amount
    if req.is_recurring and req.recurrence_interval:
        data["is_recurring"] = True
        data["recurrence_interval"] = req.recurrence_interval
        # Set next invoice date based on interval
        from dateutil.relativedelta import relativedelta
        base = req.due_date or date.today()
        intervals = {"weekly": relativedelta(weeks=1), "biweekly": relativedelta(weeks=2), "monthly": relativedelta(months=1), "quarterly": relativedelta(months=3)}
        data["next_invoice_date"] = (base + intervals.get(req.recurrence_interval, relativedelta(months=1))).isoformat()

    # Try insert with retry on invoice_number uniqueness conflict (migration 068)
    result = None
    for retry in range(3):
        if retry > 0:
            data["invoice_number"] = await _get_next_invoice_number(db, tenant_id, attempt=retry)
        try:
            result = tenant_table(db, "invoices", tenant_id).insert(data).execute()
            break
        except Exception as exc:
            error_msg = str(exc).lower()
            if ("unique" in error_msg or "duplicate" in error_msg or "idx_invoices_tenant_number" in error_msg) and retry < 2:
                logger.warning("Invoice number conflict for tenant %s, retrying (attempt %d)", tenant_id, retry + 1)
                continue
            logger.exception("Failed to create invoice for tenant %s", tenant_id)
            raise HTTPException(status_code=500, detail="Failed to create invoice")

    if not result or not result.data:
        raise HTTPException(status_code=500, detail="Failed to create invoice")

    invoice = result.data[0]
    fire_event_background(tenant_id, "invoice.created", {
        "invoice_id": invoice["id"],
        "invoice_number": invoice.get("invoice_number"),
        "total": invoice.get("total"),
        "status": invoice.get("status"),
        "lead_id": invoice.get("lead_id"),
    })
    return invoice


# ---------------------------------------------------------------------------
# Item Templates — extracted to backend.routers.invoice_item_templates
# (registered with the same /api/v1/invoices prefix in main.py BEFORE this
# router to preserve static-before-param ordering)
# ---------------------------------------------------------------------------


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
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("*")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s for tenant %s", invoice_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = result.data[0]

    # Enrich with lead details
    lead_id = invoice.get("lead_id")
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id)
                .select("id, name, email, phone")
                .eq("id", lead_id)
                .eq("client_id", tenant_id)
                .limit(1)
                .execute()
            )
            invoice["lead"] = lead_result.data[0] if lead_result.data else None
        except Exception:
            logger.warning("Could not fetch lead %s for invoice %s", lead_id, invoice_id, exc_info=True)
            invoice["lead"] = None
    else:
        invoice["lead"] = None

    return invoice


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

    # Verify invoice exists and is in draft status
    try:
        existing_result = (
            tenant_table(db, "invoices", tenant_id)
            .select("status, tax_rate, items_json")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s for update", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not existing_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    existing = existing_result.data[0]
    if existing["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit invoice with status '{existing['status']}' — only draft invoices can be updated",
        )

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}

    # Recalculate totals if items or tax_rate changed
    new_items = None
    new_tax_rate = existing.get("tax_rate", 0.0) or 0.0
    if req.items is not None:
        new_items = [item.model_dump() for item in req.items]
    if req.tax_rate is not None:
        new_tax_rate = req.tax_rate

    if req.items is not None or req.tax_rate is not None:
        items_for_calc = new_items if new_items is not None else (existing.get("items_json") or [])
        subtotal, tax_amount, total = _compute_invoice_totals(items_for_calc, new_tax_rate)
        if new_items is not None:
            updates["items_json"] = new_items
        updates["tax_rate"] = new_tax_rate
        updates["subtotal"] = subtotal
        updates["tax_amount"] = tax_amount
        updates["total"] = total

    if req.due_date is not None:
        updates["due_date"] = req.due_date.isoformat()
    if req.lead_id is not None:
        updates["lead_id"] = req.lead_id
    if req.notes is not None:
        updates["notes"] = req.notes

    if len(updates) == 1:  # only updated_at was set
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .update(updates)
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update invoice %s for tenant %s", invoice_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update invoice")

    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result.data[0]


@router.delete("/{tenant_id}/{invoice_id}")
async def delete_invoice(
    tenant_id: str,
    invoice_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete an invoice. Only allowed when status is 'draft'."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Verify invoice exists and is in draft status
    try:
        existing_result = (
            tenant_table(db, "invoices", tenant_id)
            .select("status")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s before delete", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not existing_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if existing_result.data[0]["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete invoice with status '{existing_result.data[0]['status']}' — only draft invoices can be deleted",
        )

    try:
        tenant_table(db, "invoices", tenant_id).delete().eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to delete invoice %s for tenant %s", invoice_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete invoice")

    return {"deleted": True}


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

    # Fetch invoice
    try:
        inv_result = (
            tenant_table(db, "invoices", tenant_id)
            .select("*")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s for sending", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not inv_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv_result.data[0]

    if invoice["status"] in ("paid", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send an invoice with status '{invoice['status']}'",
        )

    # Fetch tenant (business) info
    business: dict = {}
    try:
        tenant_result = (
            tenant_table(db, "tenants", tenant_id)
            .select("business_name, owner_email, phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            business = tenant_result.data[0]
    except Exception:
        logger.warning("Could not fetch tenant info for invoice send, tenant %s", tenant_id, exc_info=True)

    # Fetch lead contact details — leads table uses client_id
    lead: dict = {}
    lead_id = invoice.get("lead_id")
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id)
                .select("id, name, email, phone")
                .eq("id", lead_id)
                .eq("client_id", tenant_id)
                .limit(1)
                .execute()
            )
            if lead_result.data:
                lead = lead_result.data[0]
        except Exception:
            logger.warning("Could not fetch lead %s for invoice send", lead_id, exc_info=True)

    # Create Stripe Payment Link if not already present
    payment_link_url = invoice.get("stripe_payment_link") or ""
    if not payment_link_url and invoice.get("total", 0) > 0:
        payment_link_url = await _get_or_create_stripe_payment_link(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            invoice_number=invoice.get("invoice_number", invoice_id),
            total=float(invoice.get("total", 0)),
        ) or ""

    # Build enriched invoice dict for email rendering
    invoice_for_email = {**invoice, "stripe_payment_link": payment_link_url}

    # Send via requested channel(s)
    email_sent = False
    sms_sent = False
    errors: list[str] = []

    if req.method in ("email", "both"):
        recipient_email = lead.get("email") or ""
        if not recipient_email:
            errors.append("No email address on file for this lead")
        else:
            subject = f"Invoice {invoice.get('invoice_number', '')} from {business.get('business_name', 'Your Service Provider')}"
            body_html = _build_invoice_email_html(invoice_for_email, business, lead)
            try:
                result = await send_email(
                    to=recipient_email,
                    subject=subject,
                    body_html=body_html,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    email_sent = True
                else:
                    errors.append(f"Email failed: {result.get('detail', 'unknown error')}")
            except Exception:
                logger.exception("Unexpected error sending invoice email for invoice %s", invoice_id)
                errors.append("Email delivery failed unexpectedly")

    if req.method in ("sms", "both"):
        recipient_phone = lead.get("phone") or ""
        if not recipient_phone:
            errors.append("No phone number on file for this lead")
        else:
            invoice_number = invoice.get("invoice_number", "")
            total = float(invoice.get("total", 0))
            biz_name = business.get("business_name") or "Your Service Provider"
            if payment_link_url:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {invoice_number} for ${total:,.2f} "
                    f"from {biz_name} is ready. Pay online: {payment_link_url}"
                )
            else:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {invoice_number} for ${total:,.2f} "
                    f"from {biz_name} is ready. Please contact us to complete payment."
                )
            try:
                ok = await send_sms(to=recipient_phone, body=sms_body)
                if ok:
                    sms_sent = True
                else:
                    errors.append("SMS delivery failed")
            except Exception:
                logger.exception("Unexpected error sending invoice SMS for invoice %s", invoice_id)
                errors.append("SMS delivery failed unexpectedly")

    # Update invoice record: status, sent_at, sent_via, stripe_payment_link
    update_data: dict = {
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_via": req.method,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payment_link_url:
        update_data["stripe_payment_link"] = payment_link_url

    try:
        tenant_table(db, "invoices", tenant_id).update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to update invoice %s status after send", invoice_id)
        # Don't raise here — the send may have succeeded, we just failed to update status

    return {
        "sent": True,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "payment_link": payment_link_url,
        "errors": errors,
    }


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

    # Verify the invoice belongs to this tenant
    try:
        existing_result = (
            tenant_table(db, "invoices", tenant_id)
            .select("status")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s for mark-paid", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not existing_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current_status = existing_result.data[0]["status"]
    if current_status in ("cancelled",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark a '{current_status}' invoice as paid",
        )
    if current_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already marked as paid")

    update_data: dict = {
        "status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.payment_method:
        update_data["payment_method"] = req.payment_method

    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .update(update_data)
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to mark invoice %s as paid for tenant %s", invoice_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to mark invoice as paid")

    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    paid_invoice = result.data[0]
    fire_event_background(tenant_id, "invoice.paid", {
        "invoice_id": invoice_id,
        "invoice_number": paid_invoice.get("invoice_number"),
        "total": paid_invoice.get("total"),
        "payment_method": req.payment_method,
        "lead_id": paid_invoice.get("lead_id"),
    })
    return paid_invoice


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

    # Load current invoice
    inv = tenant_table(db, "invoices", tenant_id).select("total, amount_paid, status").eq("id", invoice_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current = inv.data[0]
    if current["status"] in ("paid", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot record payment on {current['status']} invoice")

    total = float(current.get("total") or 0)
    already_paid = float(current.get("amount_paid") or 0)
    remaining = round(total - already_paid, 2)
    if req.amount > remaining + 0.01:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds remaining balance of ${remaining:.2f}")
    new_paid = min(round(already_paid + req.amount, 2), total)

    update_data = {
        "amount_paid": new_paid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Auto-mark as paid if fully covered
    if new_paid >= total:
        update_data["status"] = "paid"
        update_data["paid_at"] = datetime.now(timezone.utc).isoformat()
        if req.payment_method:
            update_data["payment_method"] = req.payment_method

    result = tenant_table(db, "invoices", tenant_id).update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to record payment")

    return result.data[0]


class BulkSendRequest(BaseModel):
    invoice_ids: list[str] = Field(..., max_length=50)
    channel: str = Field("email", pattern="^(email|sms|both)$")


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
    sent = 0
    failed = 0
    errors = []

    # Fetch tenant info once
    business = {}
    try:
        t = tenant_table(db, "tenants", tenant_id).select("business_name").eq("id", tenant_id).limit(1).execute()
        business = t.data[0] if t.data else {}
    except Exception:
        logger.warning("Failed to fetch tenant business name for invoice send (tenant %s)", tenant_id, exc_info=True)
    biz_name = business.get("business_name") or "Your Service Provider"

    for invoice_id in req.invoice_ids:
        try:
            inv = tenant_table(db, "invoices", tenant_id).select("*").eq("id", invoice_id).eq("tenant_id", tenant_id).limit(1).execute()
            if not inv.data:
                failed += 1
                errors.append(f"{invoice_id}: not found")
                continue

            invoice = inv.data[0]
            if invoice["status"] in ("paid", "cancelled"):
                failed += 1
                errors.append(f"{invoice.get('invoice_number', invoice_id)}: already {invoice['status']}")
                continue

            lead_id = invoice.get("lead_id")
            lead = None
            if lead_id:
                lead_row = tenant_table(db, "leads", tenant_id).select("name, email, phone").eq("id", lead_id).eq("client_id", tenant_id).limit(1).execute()
                lead = lead_row.data[0] if lead_row.data else None

            if not lead or (not lead.get("email") and not lead.get("phone")):
                failed += 1
                errors.append(f"{invoice.get('invoice_number', invoice_id)}: no contact info")
                continue

            total = float(invoice.get("total") or 0)
            payment_link = invoice.get("stripe_payment_link")
            if not payment_link and total > 0:
                try:
                    payment_link = await _get_or_create_stripe_payment_link(
                        invoice_id, tenant_id, invoice.get("invoice_number", ""), total
                    )
                except Exception:
                    logger.warning("Could not create payment link for invoice %s", invoice_id, exc_info=True)

            inv_num = invoice.get("invoice_number", "")

            if req.channel in ("email", "both") and lead.get("email"):
                try:
                    subject = f"Invoice {inv_num} from {biz_name}"
                    link_html = f'<a href="{payment_link}" style="display:inline-block;padding:12px 24px;background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">Pay ${total:,.2f}</a>' if payment_link else f"<p>Amount due: ${total:,.2f}</p>"
                    html_body = f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'><h2>Invoice {inv_num}</h2><p>Hi {lead.get('name', 'there')},</p><p>You have an invoice from <strong>{biz_name}</strong> for <strong>${total:,.2f}</strong>.</p>{link_html}<p style='color:#6b7280;font-size:12px;margin-top:24px;'>-- {biz_name}</p></div>"
                    await send_email(to=lead["email"], subject=subject, body_html=html_body, tenant_id=tenant_id)
                except Exception:
                    logger.warning("Failed to email invoice %s", invoice_id, exc_info=True)

            if req.channel in ("sms", "both") and lead.get("phone"):
                try:
                    msg = f"Hi {lead.get('name', 'there')}! Invoice {inv_num} for ${total:,.2f} from {biz_name}."
                    if payment_link:
                        msg += f" Pay here: {payment_link}"
                    await send_sms(to=lead["phone"], body=msg)
                except Exception:
                    logger.warning("Failed to SMS invoice %s", invoice_id, exc_info=True)

            tenant_table(db, "invoices", tenant_id).update({
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_via": req.channel,
            }).eq("id", invoice_id).execute()

            sent += 1

        except Exception:
            failed += 1
            errors.append(f"{invoice_id}: unexpected error")
            logger.exception("Bulk send failed for invoice %s", invoice_id)

    return {"sent": sent, "failed": failed, "errors": errors[:10]}
