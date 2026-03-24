"""Invoicing & Text-to-Pay — create, send, and track invoices with Stripe Payment Links."""

import logging
from datetime import datetime, timezone, date

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.email_sender import send_email
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_invoice_totals(items: list[dict], tax_rate: float) -> tuple[float, float, float]:
    """Return (subtotal, tax_amount, total) from line items and a tax_rate percentage."""
    subtotal = round(sum(
        item.get("quantity", 1) * item.get("unit_price", 0)
        for item in items
    ), 2)
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total


async def _get_next_invoice_number(db, tenant_id: str) -> str:
    """Generate a sequential invoice number: INV-{tenant_id[:4].upper()}-{NNN}."""
    try:
        result = (
            db.table("invoices")
            .select("invoice_number")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last_num = result.data[0].get("invoice_number", "INV-XXXX-000")
            # Extract sequential portion after the last dash
            parts = last_num.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                seq = int(parts[1]) + 1
            else:
                seq = 1
        else:
            seq = 1
    except Exception:
        logger.warning("Could not determine next invoice number for tenant %s", tenant_id, exc_info=True)
        seq = 1
    prefix = tenant_id[:4].upper()
    return f"INV-{prefix}-{seq:03d}"


async def _get_or_create_stripe_payment_link(invoice_id: str, tenant_id: str, invoice_number: str, total: float) -> str | None:
    """Create a Stripe Payment Link for the invoice total. Returns the URL or None on failure."""
    if not settings.stripe_secret_key:
        logger.warning("Stripe not configured — cannot create payment link for invoice %s", invoice_id)
        return None

    stripe.api_key = settings.stripe_secret_key
    try:
        price = stripe.Price.create(
            unit_amount=int(round(total * 100)),  # cents
            currency="usd",
            product_data={"name": f"Invoice {invoice_number}"},
        )
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )
        return payment_link.url
    except stripe.StripeError as e:
        logger.warning("Stripe error creating payment link for invoice %s: %s", invoice_id, str(e))
        return None
    except Exception:
        logger.exception("Unexpected error creating Stripe payment link for invoice %s", invoice_id)
        return None


def _build_invoice_email_html(invoice: dict, business: dict, lead: dict) -> str:
    """Build a professional HTML email body for an invoice with payment link."""
    biz_name = business.get("business_name") or "Your Service Provider"
    biz_email = business.get("owner_email") or ""

    cust_name = lead.get("name") or "Valued Customer"
    invoice_number = invoice.get("invoice_number") or "N/A"
    total = invoice.get("total", 0)
    due_date = invoice.get("due_date") or ""
    notes = invoice.get("notes") or ""
    payment_link = invoice.get("stripe_payment_link") or ""
    items = invoice.get("items_json") or []
    subtotal = invoice.get("subtotal", 0)
    tax_amount = invoice.get("tax_amount", 0)

    due_section = f"<p style='color:#4b5563;'>Due: <strong>{due_date}</strong></p>" if due_date else ""
    notes_section = f"<p style='color:#4b5563;margin-top:16px;'>{notes}</p>" if notes else ""

    pay_button = ""
    if payment_link:
        pay_button = (
            f"<div style='text-align:center;margin:32px 0;'>"
            f"<a href='{payment_link}' style='background:#2563eb;color:#ffffff;padding:14px 32px;"
            f"border-radius:6px;text-decoration:none;font-size:16px;font-weight:600;display:inline-block;'>"
            f"Pay Now — ${total:,.2f}</a></div>"
        )

    rows = ""
    for item in items:
        desc = item.get("description", "")
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        line_total = round(qty * unit_price, 2)
        rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{desc}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center;'>{qty}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${unit_price:,.2f}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${line_total:,.2f}</td>"
            f"</tr>"
        )

    tax_row = ""
    if tax_amount and tax_amount > 0:
        tax_row = (
            f"<tr><td colspan='3' style='text-align:right;padding:4px 12px;color:#6b7280;'>Tax</td>"
            f"<td style='text-align:right;padding:4px 12px;color:#6b7280;'>${tax_amount:,.2f}</td></tr>"
        )

    return f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:28px 32px;border-radius:8px 8px 0 0;">
    <h1 style="color:#ffffff;margin:0;font-size:22px;">{biz_name}</h1>
    <p style="color:rgba(255,255,255,0.85);margin:4px 0 0 0;font-size:14px;">Invoice {invoice_number}</p>
  </div>
  <div style="background:#ffffff;padding:28px 32px;border:1px solid #e5e7eb;border-top:none;">
    <p style="color:#374151;font-size:16px;">Hi {cust_name},</p>
    <p style="color:#4b5563;">Please find your invoice from {biz_name} below.</p>
    {due_section}

    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Description</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Qty</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Unit Price</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Total</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
      <tfoot>
        <tr>
          <td colspan="3" style="text-align:right;padding:8px 12px;color:#4b5563;border-top:1px solid #e5e7eb;">Subtotal</td>
          <td style="text-align:right;padding:8px 12px;color:#4b5563;border-top:1px solid #e5e7eb;">${subtotal:,.2f}</td>
        </tr>
        {tax_row}
        <tr>
          <td colspan="3" style="text-align:right;padding:10px 12px;font-size:16px;font-weight:700;color:#1e3a5f;border-top:2px solid #1e3a5f;">Total Due</td>
          <td style="text-align:right;padding:10px 12px;font-size:16px;font-weight:700;color:#1e3a5f;border-top:2px solid #1e3a5f;">${total:,.2f}</td>
        </tr>
      </tfoot>
    </table>

    {pay_button}
    {notes_section}

    <p style="color:#6b7280;font-size:13px;margin-top:24px;">
      Questions? Contact us at {biz_email}
    </p>
  </div>
  <div style="background:#f9fafb;padding:12px 32px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">Sent via AgentNexLiFy</p>
  </div>
</div>
"""


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

    db = get_supabase()
    try:
        result = (
            db.table("invoices")
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

    db = get_supabase()

    # Fetch the bid
    try:
        bid_result = (
            db.table("bids")
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
            db.table("invoices")
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
        result = db.table("invoices").insert(data).execute()
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

    db = get_supabase()
    try:
        query = (
            db.table("invoices")
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
                db.table("leads")
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

    db = get_supabase()
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

    try:
        result = db.table("invoices").insert(data).execute()
    except Exception:
        logger.exception("Failed to create invoice for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create invoice")

    if not result.data:
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
# Bulk Invoice Generation
# Must be before /{tenant_id}/{invoice_id} to avoid route shadowing
# ---------------------------------------------------------------------------


class BulkInvoiceRequest(BaseModel):
    lead_ids: list[str] = Field(..., max_length=50, description="Up to 50 lead IDs")
    items: list[InvoiceItemModel] = Field(..., min_length=1)
    tax_rate: float = Field(0.0, ge=0, le=100)
    due_date: date | None = None
    notes: str | None = Field(None, max_length=5000)
    auto_send: bool = Field(False, description="Automatically send invoices after creation")
    send_method: str = Field("email", pattern="^(email|sms|both)$")


@router.post("/{tenant_id}/bulk", status_code=201)
async def create_bulk_invoices(
    tenant_id: str,
    req: BulkInvoiceRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create invoices for multiple leads at once.

    Useful for monthly service businesses (lawn care, cleaning, etc.)
    that bill the same amount to many clients. Max 50 leads per request.
    Optionally auto-sends via email/SMS after creation.
    """
    verify_tenant(claims, tenant_id)

    if len(req.lead_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 leads per bulk operation")
    if len(req.lead_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one lead_id required")

    items = [item.model_dump() for item in req.items]
    subtotal, tax_amount, total = _compute_invoice_totals(items, req.tax_rate)

    db = get_supabase()

    # Fetch lead info for all leads at once
    try:
        leads_result = (
            db.table("leads")
            .select("id, name, email, phone")
            .eq("client_id", tenant_id)
            .in_("id", req.lead_ids)
            .execute()
        )
    except Exception:
        logger.exception("bulk_invoices: failed to fetch leads for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch leads")

    lead_map = {l["id"]: l for l in (leads_result.data or [])}

    created = []
    failed = []

    for lead_id in req.lead_ids:
        lead = lead_map.get(lead_id)
        if not lead:
            failed.append({"lead_id": lead_id, "reason": "Lead not found"})
            continue

        try:
            invoice_number = await _get_next_invoice_number(db, tenant_id)
            data = {
                "tenant_id": tenant_id,
                "lead_id": lead_id,
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
            if req.notes is not None:
                data["notes"] = req.notes

            result = db.table("invoices").insert(data).execute()
            if result.data:
                invoice = result.data[0]
                created.append(invoice)
                fire_event_background(tenant_id, "invoice.created", {
                    "invoice_id": invoice["id"],
                    "invoice_number": invoice.get("invoice_number"),
                    "total": invoice.get("total"),
                    "lead_id": lead_id,
                })
            else:
                failed.append({"lead_id": lead_id, "reason": "Insert returned no data"})
        except Exception as exc:
            logger.warning("bulk_invoices: failed for lead %s: %s", lead_id, exc)
            failed.append({"lead_id": lead_id, "reason": str(exc)[:200]})

    # Auto-send if requested
    sent_count = 0
    if req.auto_send and created:
        tenant_result = (
            db.table("tenants")
            .select("business_name, owner_email")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        business_name = "Your Business"
        if tenant_result.data:
            business_name = tenant_result.data[0].get("business_name") or "Your Business"

        for invoice in created:
            inv_lead_id = invoice.get("lead_id")
            lead = lead_map.get(inv_lead_id, {})
            inv_number = invoice.get("invoice_number", "")
            inv_total = invoice.get("total", 0)

            try:
                if req.send_method in ("email", "both") and lead.get("email"):
                    await send_email(
                        to=lead["email"],
                        subject=f"Invoice {inv_number} from {business_name}",
                        body_html=(
                            f"<h2>Invoice {inv_number}</h2>"
                            f"<p>Amount due: <strong>${inv_total:.2f}</strong></p>"
                            f"<p>Please contact us for payment details.</p>"
                            f"<p>Best regards,<br>{business_name}</p>"
                        ),
                        tenant_id=tenant_id,
                        lead_id=inv_lead_id or "",
                    )
                if req.send_method in ("sms", "both") and lead.get("phone"):
                    await send_sms(
                        lead["phone"],
                        f"{business_name}: Invoice {inv_number} for ${inv_total:.2f} has been sent. Please contact us for payment details.",
                    )

                # Update status to sent
                db.table("invoices").update({
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "sent_via": req.send_method,
                }).eq("id", invoice["id"]).execute()
                sent_count += 1
            except Exception:
                logger.warning("bulk_invoices: failed to send invoice %s", invoice.get("id"), exc_info=True)

    return {
        "created_count": len(created),
        "failed_count": len(failed),
        "sent_count": sent_count,
        "created": created,
        "failed": failed,
    }


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
    db = get_supabase()
    result = (
        db.table("invoice_item_templates")
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
    db = get_supabase()
    result = db.table("invoice_item_templates").insert({
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
    db = get_supabase()
    result = (
        db.table("invoice_item_templates")
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
    db = get_supabase()
    result = (
        db.table("invoice_item_templates")
        .update({"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}


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

    db = get_supabase()
    try:
        result = (
            db.table("invoices")
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
                db.table("leads")
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

    db = get_supabase()

    # Verify invoice exists and is in draft status
    try:
        existing_result = (
            db.table("invoices")
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
            db.table("invoices")
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

    db = get_supabase()

    # Verify invoice exists and is in draft status
    try:
        existing_result = (
            db.table("invoices")
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
        db.table("invoices").delete().eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
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

    db = get_supabase()

    # Fetch invoice
    try:
        inv_result = (
            db.table("invoices")
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
            db.table("tenants")
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
                db.table("leads")
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
        db.table("invoices").update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
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

    db = get_supabase()

    # Verify the invoice belongs to this tenant
    try:
        existing_result = (
            db.table("invoices")
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
            db.table("invoices")
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
    db = get_supabase()

    # Load current invoice
    inv = db.table("invoices").select("total, amount_paid, status").eq("id", invoice_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current = inv.data[0]
    if current["status"] in ("paid", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot record payment on {current['status']} invoice")

    new_paid = round(float(current.get("amount_paid") or 0) + req.amount, 2)
    total = float(current.get("total") or 0)

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

    result = db.table("invoices").update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to record payment")

    return result.data[0]
