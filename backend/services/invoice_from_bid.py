"""Create an invoice from an accepted bid.

Extracted from ``backend/routers/invoices.py`` to keep the router thin and
allow the bid-to-invoice conversion to be independently tested.

Raises:
- 404 when the bid does not exist
- 400 when the bid is not in 'accepted' status
- 409 when an invoice already exists for this bid
- 500 on database failures (fetch or insert)
"""

import logging

from fastapi import HTTPException

from backend.services.invoice_calculations import compute_invoice_totals
from backend.services.invoice_numbering import get_next_invoice_number
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _fetch_bid(db, tenant_id: str, bid_id: str) -> dict:
    try:
        result = (
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

    if not result.data:
        raise HTTPException(status_code=404, detail="Bid not found")
    return result.data[0]


def _check_for_existing_invoice(db, tenant_id: str, bid_id: str) -> None:
    """Raise 409 if an invoice already exists for this bid. Best-effort check."""
    try:
        existing = (
            tenant_table(db, "invoices", tenant_id)
            .select("id, invoice_number")
            .eq("tenant_id", tenant_id)
            .eq("bid_id", bid_id)
            .limit(1)
            .execute()
        )
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "Could not check for existing invoice from bid %s", bid_id, exc_info=True
        )
        return

    if existing.data:
        invoice_number = existing.data[0].get("invoice_number", "")
        raise HTTPException(
            status_code=409,
            detail=f"An invoice ({invoice_number}) already exists for this bid",
        )


def _normalize_bid_items(bid_items_raw: list) -> list[dict]:
    return [
        {
            "description": item.get("description", ""),
            "quantity": item.get("quantity", 1),
            "unit_price": item.get("unit_price", 0),
        }
        for item in bid_items_raw
    ]


async def create_invoice_from_bid_for_tenant(
    db, tenant_id: str, bid_id: str
) -> dict:
    """Create an invoice from an accepted bid. Returns the created invoice row."""
    bid = _fetch_bid(db, tenant_id, bid_id)

    if bid.get("status") != "accepted":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bid status is '{bid.get('status')}' — "
                "only accepted bids can be converted to invoices"
            ),
        )

    _check_for_existing_invoice(db, tenant_id, bid_id)

    invoice_items = _normalize_bid_items(bid.get("items_json") or [])
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
        logger.exception(
            "Failed to create invoice from bid %s for tenant %s", bid_id, tenant_id
        )
        raise HTTPException(
            status_code=500, detail="Failed to create invoice from bid"
        )

    if not result.data:
        raise HTTPException(
            status_code=500, detail="Failed to create invoice from bid"
        )
    return result.data[0]
