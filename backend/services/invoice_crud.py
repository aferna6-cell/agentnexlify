"""Invoice CRUD + payment flows (issue #473 split). Moved verbatim from
routers/invoices.py; each flow backs exactly one route and raises
HTTPException like the route did (established services pattern).

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timezone, date

from fastapi import HTTPException

from backend.services.invoice_helpers import (
    compute_invoice_totals,
    get_next_invoice_number,
)
from backend.services.tenant_scope import tenant_table
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)


async def create_invoice_flow(db, tenant_id: str, req) -> dict:
    """Create a new invoice from an InvoiceCreate payload."""
    items = [item.model_dump() for item in req.items]
    subtotal, tax_amount, total = compute_invoice_totals(items, req.tax_rate)

    if req.deposit_amount > total:
        raise HTTPException(status_code=400, detail="deposit_amount cannot exceed invoice total")

    invoice_number = await get_next_invoice_number(db, tenant_id)

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
            data["invoice_number"] = await get_next_invoice_number(db, tenant_id, attempt=retry)
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


async def create_invoice_from_bid_flow(db, tenant_id: str, bid_id: str) -> dict:
    """Create an invoice by copying items and amounts from an accepted bid."""
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

    subtotal, tax_amount, total = compute_invoice_totals(invoice_items, 0.0)
    invoice_number = await get_next_invoice_number(db, tenant_id)

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


async def list_invoices_flow(db, tenant_id: str, status: str | None, lead_id: str | None, offset: int, limit: int) -> dict:
    """List invoices with lead-name enrichment and pagination envelope."""
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


async def get_invoice_flow(db, tenant_id: str, invoice_id: str) -> dict:
    """Fetch one invoice with its lead attached."""
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


async def update_invoice_flow(db, tenant_id: str, invoice_id: str, req) -> dict:
    """Update a draft invoice from an InvoiceUpdate payload, recalculating totals."""
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
        subtotal, tax_amount, total = compute_invoice_totals(items_for_calc, new_tax_rate)
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


async def delete_invoice_flow(db, tenant_id: str, invoice_id: str) -> dict:
    """Delete a draft invoice."""
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


async def mark_invoice_paid_flow(db, tenant_id: str, invoice_id: str, payment_method: str | None) -> dict:
    """Manually mark an invoice as paid; fires the invoice.paid webhook."""
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
    if payment_method:
        update_data["payment_method"] = payment_method

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
        "payment_method": payment_method,
        "lead_id": paid_invoice.get("lead_id"),
    })
    return paid_invoice


async def record_partial_payment_flow(db, tenant_id: str, invoice_id: str, amount: float, payment_method: str | None) -> dict:
    """Record a partial payment; auto-marks paid when the balance is covered."""
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
    if amount > remaining + 0.01:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds remaining balance of ${remaining:.2f}")
    new_paid = min(round(already_paid + amount, 2), total)

    update_data = {
        "amount_paid": new_paid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Auto-mark as paid if fully covered
    if new_paid >= total:
        update_data["status"] = "paid"
        update_data["paid_at"] = datetime.now(timezone.utc).isoformat()
        if payment_method:
            update_data["payment_method"] = payment_method

    result = tenant_table(db, "invoices", tenant_id).update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to record payment")

    return result.data[0]
