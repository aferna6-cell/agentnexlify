"""Bid-specific routes — get/update/delete/status/PDF for individual bids.

Endpoints all use the `{bid_id}` path parameter and MUST be registered AFTER
`bids_static.py` to avoid shadowing /{tenant_id}/stats etc.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.routers.bids_models import (
    BidStatusUpdate,
    BidUpdate,
    _verify_tenant,
    logger,
)
from backend.services.bid_rendering import compute_totals, render_bid_html

router = APIRouter()


@router.get("/{tenant_id}/{bid_id}")
async def get_bid(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single bid by ID."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("bids")
            .select("*")
            .eq("id", bid_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch bid %s for tenant %s", bid_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid")

    if not result.data:
        raise HTTPException(status_code=404, detail="Bid not found")
    return result.data[0]


@router.put("/{tenant_id}/{bid_id}")
async def update_bid(
    tenant_id: str,
    bid_id: str,
    req: BidUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a bid."""
    _verify_tenant(claims, tenant_id)

    updates: dict = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.description is not None:
        updates["description"] = req.description
    if req.terms is not None:
        updates["terms"] = req.terms
    if req.timeline is not None:
        updates["timeline"] = req.timeline
    if req.warranty is not None:
        updates["warranty"] = req.warranty
    if req.lead_id is not None:
        updates["lead_id"] = req.lead_id
    if req.items_json is not None:
        items = [item.model_dump() for item in req.items_json]
        subtotal, tax, total = compute_totals(items)
        updates["items_json"] = items
        updates["subtotal"] = subtotal
        updates["tax"] = tax
        updates["total"] = total

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    try:
        result = (
            db.table("bids")
            .update(updates)
            .eq("id", bid_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update bid %s for tenant %s", bid_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update bid")

    if not result.data:
        raise HTTPException(status_code=404, detail="Bid not found")
    return result.data[0]


@router.delete("/{tenant_id}/{bid_id}")
async def delete_bid(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a bid."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        db.table("bids").delete().eq("id", bid_id).eq(
            "tenant_id", tenant_id
        ).execute()
    except Exception:
        logger.exception("Failed to delete bid %s for tenant %s", bid_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete bid")

    return {"deleted": True}


@router.put("/{tenant_id}/{bid_id}/status")
async def update_bid_status(
    tenant_id: str,
    bid_id: str,
    req: BidStatusUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a bid's status (draft -> sent -> viewed -> accepted/rejected/expired)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    try:
        existing = (
            db.table("bids")
            .select("status")
            .eq("id", bid_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch bid %s for status update", bid_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid")

    if not existing.data:
        raise HTTPException(status_code=404, detail="Bid not found")

    current_status = existing.data[0]["status"]

    valid_transitions: dict[str, set[str]] = {
        "draft": {"sent"},
        "sent": {"viewed", "accepted", "rejected", "expired"},
        "viewed": {"accepted", "rejected", "expired"},
        "accepted": set(),
        "rejected": {"draft"},
        "expired": {"draft"},
    }

    if req.status not in valid_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current_status}' to '{req.status}'",
        )

    updates: dict = {"status": req.status}
    if req.status == "sent":
        updates["sent_at"] = datetime.now(timezone.utc).isoformat()
    elif req.status == "viewed":
        updates["viewed_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = (
            db.table("bids")
            .update(updates)
            .eq("id", bid_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update bid %s status", bid_id)
        raise HTTPException(status_code=500, detail="Failed to update bid status")

    if not result.data:
        raise HTTPException(status_code=404, detail="Bid not found")
    return result.data[0]


@router.post("/{tenant_id}/{bid_id}/pdf")
async def generate_bid_pdf(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate a branded HTML document for a bid that can be printed to PDF.

    Returns an HTML page with professional styling and a print button.
    The browser's print dialog can save as PDF.
    """
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
        logger.exception("Failed to fetch bid %s for PDF generation", bid_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid")

    if not bid_result.data:
        raise HTTPException(status_code=404, detail="Bid not found")

    bid = bid_result.data[0]

    business: dict = {}
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, owner_email, phone, city")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            business = tenant_result.data[0]
    except Exception:
        logger.warning("Could not fetch tenant info for bid PDF, tenant %s", tenant_id, exc_info=True)

    # Fetch customer info if lead_id is set — leads table uses client_id
    customer: dict = {}
    lead_id = bid.get("lead_id")
    if lead_id:
        try:
            lead_result = (
                db.table("leads")
                .select("name, email, phone")
                .eq("id", lead_id)
                .eq("client_id", tenant_id)
                .limit(1)
                .execute()
            )
            if lead_result.data:
                customer = lead_result.data[0]
        except Exception:
            logger.warning("Could not fetch lead %s for bid PDF", lead_id, exc_info=True)

    html = render_bid_html(bid, business, customer)

    pdf_url = f"/api/v1/bids/{tenant_id}/{bid_id}/pdf"
    try:
        db.table("bids").update({"pdf_url": pdf_url}).eq("id", bid_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.warning("Could not save pdf_url for bid %s", bid_id, exc_info=True)

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="bid-{bid_id[:8]}.html"'},
    )
