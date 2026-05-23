"""Invoice payment state changes — mark paid, record partial payment.

Pulled out of ``backend/routers/invoices.py`` to keep the router thin. Each
function returns the updated invoice row and raises ``HTTPException`` for the
caller to surface unchanged.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.services.tenant_scope import tenant_table
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)


async def mark_invoice_as_paid(
    db, tenant_id: str, invoice_id: str, payment_method: str | None
) -> dict:
    """Mark a non-paid/non-cancelled invoice as fully paid."""
    try:
        existing = (
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

    if not existing.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current_status = existing.data[0]["status"]
    if current_status == "cancelled":
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
        logger.exception(
            "Failed to mark invoice %s as paid for tenant %s", invoice_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to mark invoice as paid")

    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    paid_invoice = result.data[0]
    fire_event_background(
        tenant_id,
        "invoice.paid",
        {
            "invoice_id": invoice_id,
            "invoice_number": paid_invoice.get("invoice_number"),
            "total": paid_invoice.get("total"),
            "payment_method": payment_method,
            "lead_id": paid_invoice.get("lead_id"),
        },
    )
    return paid_invoice


async def record_partial_payment_amount(
    db, tenant_id: str, invoice_id: str, amount: float, payment_method: str | None
) -> dict:
    """Record a partial payment; auto-promotes to ``paid`` when fully covered."""
    inv = (
        tenant_table(db, "invoices", tenant_id)
        .select("total, amount_paid, status")
        .eq("id", invoice_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current = inv.data[0]
    if current["status"] in ("paid", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot record payment on {current['status']} invoice",
        )

    total = float(current.get("total") or 0)
    already_paid = float(current.get("amount_paid") or 0)
    remaining = round(total - already_paid, 2)
    if amount > remaining + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount exceeds remaining balance of ${remaining:.2f}",
        )
    new_paid = min(round(already_paid + amount, 2), total)

    update_data: dict = {
        "amount_paid": new_paid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if new_paid >= total:
        update_data["status"] = "paid"
        update_data["paid_at"] = datetime.now(timezone.utc).isoformat()
        if payment_method:
            update_data["payment_method"] = payment_method

    result = (
        tenant_table(db, "invoices", tenant_id)
        .update(update_data)
        .eq("id", invoice_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to record payment")

    return result.data[0]
