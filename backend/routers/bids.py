"""Contractor Bid Manager — CRUD for bids, bid templates, AI bid generation, and stats."""

import json
import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bids", tags=["bids"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class BidItemModel(BaseModel):
    description: str = Field(..., max_length=500)
    quantity: float = Field(1.0, ge=0)
    unit: str = Field("each", max_length=50)
    unit_price: float = Field(0.0, ge=0)
    total: float = Field(0.0, ge=0)


class BidCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = Field(None, max_length=5000)
    items_json: list[BidItemModel] = Field(default_factory=list)
    terms: str | None = Field(None, max_length=5000)
    timeline: str | None = Field(None, max_length=1000)
    warranty: str | None = Field(None, max_length=2000)
    lead_id: str | None = None


class BidUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=5000)
    items_json: list[BidItemModel] | None = None
    terms: str | None = Field(None, max_length=5000)
    timeline: str | None = Field(None, max_length=1000)
    warranty: str | None = Field(None, max_length=2000)
    lead_id: str | None = None


class BidStatusUpdate(BaseModel):
    status: str = Field(
        ..., pattern="^(draft|sent|viewed|accepted|rejected|expired)$"
    )


class BidTemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    default_items: list[BidItemModel] = Field(default_factory=list)


class AIBidGenerateRequest(BaseModel):
    job_description: str = Field(..., max_length=3000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _compute_totals(items: list[dict]) -> tuple[float, float, float]:
    """Compute subtotal, tax (0 for now), and total from line items."""
    subtotal = 0.0
    for item in items:
        line_total = item.get("total", 0.0)
        if line_total == 0.0:
            line_total = item.get("quantity", 1) * item.get("unit_price", 0)
            item["total"] = round(line_total, 2)
        subtotal += line_total
    subtotal = round(subtotal, 2)
    tax = 0.0
    total = round(subtotal + tax, 2)
    return subtotal, tax, total


# ---------------------------------------------------------------------------
# Bid CRUD
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}")
async def list_bids(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List bids for a tenant with optional status filter and pagination."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        query = (
            db.table("bids")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("status", status)
        # Supabase uses range() for offset/limit pagination
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
    except Exception:
        logger.exception("Failed to list bids for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list bids")

    return {
        "bids": result.data or [],
        "count": result.count or len(result.data or []),
        "offset": offset,
        "limit": limit,
    }


@router.post("/{tenant_id}", status_code=201)
async def create_bid(
    tenant_id: str,
    req: BidCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new bid."""
    _verify_tenant(claims, tenant_id)

    items = [item.model_dump() for item in req.items_json]
    subtotal, tax, total = _compute_totals(items)

    data = {
        "tenant_id": tenant_id,
        "title": req.title,
        "description": req.description,
        "items_json": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "terms": req.terms,
        "timeline": req.timeline,
        "warranty": req.warranty,
        "status": "draft",
    }
    if req.lead_id:
        data["lead_id"] = req.lead_id

    db = get_supabase()
    try:
        result = db.table("bids").insert(data).execute()
    except Exception:
        logger.exception("Failed to create bid for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create bid")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create bid")
    return result.data[0]


@router.get("/{tenant_id}/stats")
async def bid_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return bid statistics: total bids, win rate, average value, pipeline value."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("bids")
            .select("status, total")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch bid stats for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid stats")

    bids = result.data or []
    total_bids = len(bids)

    # Only count sent, viewed, accepted, rejected as "resolved" for win rate
    sent_or_decided = [
        b for b in bids if b.get("status") in ("sent", "viewed", "accepted", "rejected", "expired")
    ]
    accepted_count = sum(1 for b in bids if b.get("status") == "accepted")
    win_rate = round(accepted_count / len(sent_or_decided) * 100, 1) if sent_or_decided else 0.0

    all_totals = [float(b.get("total", 0)) for b in bids]
    avg_value = round(sum(all_totals) / len(all_totals), 2) if all_totals else 0.0

    # Pipeline value: sum of bids in sent or viewed status
    pipeline_value = round(
        sum(float(b.get("total", 0)) for b in bids if b.get("status") in ("sent", "viewed")),
        2,
    )

    return {
        "total_bids": total_bids,
        "win_rate": win_rate,
        "accepted_count": accepted_count,
        "avg_value": avg_value,
        "pipeline_value": pipeline_value,
    }


@router.get("/{tenant_id}/templates")
async def list_bid_templates(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List bid templates for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("bid_templates")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list bid templates for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list bid templates")

    return {"templates": result.data or [], "count": len(result.data or [])}


@router.post("/{tenant_id}/templates", status_code=201)
async def create_bid_template(
    tenant_id: str,
    req: BidTemplateCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a reusable bid template."""
    _verify_tenant(claims, tenant_id)

    data = {
        "tenant_id": tenant_id,
        "name": req.name,
        "description": req.description,
        "default_items": [item.model_dump() for item in req.default_items],
    }

    db = get_supabase()
    try:
        result = db.table("bid_templates").insert(data).execute()
    except Exception:
        logger.exception("Failed to create bid template for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create bid template")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create bid template")
    return result.data[0]


@router.delete("/{tenant_id}/templates/{template_id}")
async def delete_bid_template(
    tenant_id: str,
    template_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a bid template."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        db.table("bid_templates").delete().eq("id", template_id).eq(
            "tenant_id", tenant_id
        ).execute()
    except Exception:
        logger.exception("Failed to delete bid template %s", template_id)
        raise HTTPException(status_code=500, detail="Failed to delete bid template")

    return {"deleted": True}


@router.post("/{tenant_id}/ai-generate")
async def ai_generate_bid(
    tenant_id: str,
    req: AIBidGenerateRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """AI generates a structured bid from a plain-language job description.

    Example input: "3-bedroom house, full interior paint, medium quality, Clemson SC"
    Returns structured bid items ready to save.
    """
    _verify_tenant(claims, tenant_id)

    # Fetch business context
    db = get_supabase()
    biz_name = ""
    biz_type = ""
    city = ""
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            biz_name = tenant_result.data[0].get("business_name", "")
            biz_type = tenant_result.data[0].get("business_type", "")
            city = tenant_result.data[0].get("city", "")
    except Exception:
        logger.warning("Could not fetch tenant info for AI bid generation", exc_info=True)

    context = f"Business: {biz_name}" if biz_name else ""
    if biz_type:
        context += f" ({biz_type})"
    if city:
        context += f" in {city}"

    prompt = (
        "You are a professional contractor bid estimator. Based on the job description below, "
        "generate a detailed bid with line items, pricing, terms, timeline, and warranty.\n\n"
        f"Job description: \"{req.job_description}\"\n\n"
        f"{context}\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "title": "Short bid title",\n'
        '  "description": "1-2 paragraph summary of the scope of work",\n'
        '  "items": [\n'
        '    {"description": "Line item name", "quantity": 1, "unit": "sqft", "unit_price": 3.50, "total": 350.00}\n'
        "  ],\n"
        '  "terms": "Payment terms (e.g., 50% upfront, 50% on completion)",\n'
        '  "timeline": "Estimated duration (e.g., 5-7 business days)",\n'
        '  "warranty": "Warranty details (e.g., 2-year warranty on workmanship)"\n'
        "}\n\n"
        "Rules:\n"
        "- Generate realistic line items with materials and labor separated\n"
        "- Use market-rate pricing for the area if a location is given\n"
        "- Each item must have description, quantity, unit, unit_price, and total (quantity * unit_price)\n"
        "- Include at least 3 line items\n"
        "- Terms should be professional and standard for the trade\n"
        "- Output ONLY the JSON object, no markdown fences or extra text"
    )

    try:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=30.0
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON -- handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0].strip()

        result = json.loads(text)

        # Normalize the response to match our schema
        items = result.get("items", [])
        for item in items:
            if "total" not in item or item["total"] == 0:
                item["total"] = round(
                    item.get("quantity", 1) * item.get("unit_price", 0), 2
                )

        subtotal = round(sum(i.get("total", 0) for i in items), 2)

        return {
            "title": result.get("title", "Untitled Bid"),
            "description": result.get("description"),
            "items_json": items,
            "subtotal": subtotal,
            "tax": 0.0,
            "total": subtotal,
            "terms": result.get("terms"),
            "timeline": result.get("timeline"),
            "warranty": result.get("warranty"),
        }
    except json.JSONDecodeError:
        logger.warning("AI bid generator returned invalid JSON: %s", text[:300])
        raise HTTPException(
            status_code=502, detail="AI returned invalid response -- try again"
        )
    except anthropic.APIError as e:
        logger.warning("Anthropic API error in AI bid generator: %s", str(e))
        raise HTTPException(
            status_code=502, detail="AI service error -- try again"
        )
    except Exception:
        logger.exception("Unexpected error in AI bid generator")
        raise HTTPException(
            status_code=500, detail="Failed to generate bid -- try again"
        )


@router.get("/{tenant_id}/{bid_id}")
async def get_bid(
    tenant_id: str,
    bid_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single bid by ID."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
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
        subtotal, tax, total = _compute_totals(items)
        updates["items_json"] = items
        updates["subtotal"] = subtotal
        updates["tax"] = tax
        updates["total"] = total

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()

    # Fetch current bid to validate status transition
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

    # Valid transitions
    valid_transitions: dict[str, set[str]] = {
        "draft": {"sent"},
        "sent": {"viewed", "accepted", "rejected", "expired"},
        "viewed": {"accepted", "rejected", "expired"},
        "accepted": set(),
        "rejected": {"draft"},  # allow re-drafting a rejected bid
        "expired": {"draft"},   # allow re-drafting an expired bid
    }

    if req.status not in valid_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current_status}' to '{req.status}'",
        )

    updates: dict = {"status": req.status}
    # Set timestamps for key transitions
    if req.status == "sent":
        from datetime import datetime, timezone
        updates["sent_at"] = datetime.now(timezone.utc).isoformat()
    elif req.status == "viewed":
        from datetime import datetime, timezone
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
