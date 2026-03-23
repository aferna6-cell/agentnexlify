"""Contractor Bid Manager — CRUD for bids, bid templates, AI bid generation, PDF, and stats."""

import json
import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
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
            biz_name = tenant_result.data[0].get("business_name") or ""
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


# ---------------------------------------------------------------------------
# PDF (HTML) Generation
# ---------------------------------------------------------------------------

def _build_bid_html(bid: dict, business: dict, customer: dict) -> str:
    """Build a professional, print-friendly HTML document for a bid."""
    biz_name = business.get("business_name") or "Business"
    biz_email = business.get("owner_email") or ""
    biz_phone = business.get("phone") or ""
    biz_city = business.get("city") or ""

    cust_name = customer.get("name") or ""
    cust_email = customer.get("email") or ""
    cust_phone = customer.get("phone") or ""

    title = bid.get("title") or "Bid"
    description = bid.get("description") or ""
    items = bid.get("items_json") or []
    subtotal = bid.get("subtotal", 0)
    tax = bid.get("tax", 0)
    total = bid.get("total", 0)
    terms = bid.get("terms") or ""
    timeline = bid.get("timeline") or ""
    warranty = bid.get("warranty") or ""
    bid_status = bid.get("status") or "draft"
    created_at = bid.get("created_at") or ""

    # Format date
    date_display = ""
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            date_display = dt.strftime("%B %d, %Y")
        except Exception:
            date_display = created_at[:10] if len(created_at) >= 10 else created_at

    # Build line items rows
    items_rows = ""
    for i, item in enumerate(items, 1):
        desc = item.get("description", "")
        qty = item.get("quantity", 1)
        unit = item.get("unit", "each")
        unit_price = item.get("unit_price", 0)
        line_total = item.get("total", 0)
        items_rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{i}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{desc}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center;'>{qty} {unit}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${unit_price:,.2f}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;'>${line_total:,.2f}</td>"
            f"</tr>"
        )

    # Build optional sections
    terms_section = ""
    if terms:
        terms_section = (
            f"<div style='margin-top:24px;'>"
            f"<h3 style='font-size:14px;color:#374151;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.5px;'>Payment Terms</h3>"
            f"<p style='margin:0;color:#4b5563;line-height:1.6;'>{terms}</p>"
            f"</div>"
        )
    timeline_section = ""
    if timeline:
        timeline_section = (
            f"<div style='margin-top:24px;'>"
            f"<h3 style='font-size:14px;color:#374151;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.5px;'>Timeline</h3>"
            f"<p style='margin:0;color:#4b5563;line-height:1.6;'>{timeline}</p>"
            f"</div>"
        )
    warranty_section = ""
    if warranty:
        warranty_section = (
            f"<div style='margin-top:24px;'>"
            f"<h3 style='font-size:14px;color:#374151;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.5px;'>Warranty</h3>"
            f"<p style='margin:0;color:#4b5563;line-height:1.6;'>{warranty}</p>"
            f"</div>"
        )

    customer_block = ""
    if cust_name or cust_email or cust_phone:
        customer_block = (
            f"<div>"
            f"<h3 style='font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 8px 0;'>Prepared For</h3>"
            f"<p style='margin:0;font-weight:600;color:#111827;'>{cust_name}</p>"
            + (f"<p style='margin:2px 0;color:#4b5563;'>{cust_email}</p>" if cust_email else "")
            + (f"<p style='margin:2px 0;color:#4b5563;'>{cust_phone}</p>" if cust_phone else "")
            + "</div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {biz_name}</title>
<style>
  @media print {{
    body {{ margin: 0; padding: 0; }}
    .no-print {{ display: none !important; }}
    @page {{ margin: 0.75in; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #111827; margin: 0; padding: 0; background: #f9fafb; }}
</style>
</head>
<body>
<div style="max-width:800px;margin:24px auto;background:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:32px 40px;color:#ffffff;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
      <div>
        <h1 style="margin:0;font-size:28px;font-weight:700;">{biz_name}</h1>
        <p style="margin:4px 0 0 0;opacity:0.85;font-size:14px;">{biz_email}{(' | ' + biz_phone) if biz_phone else ''}{(' | ' + biz_city) if biz_city else ''}</p>
      </div>
      <div style="text-align:right;">
        <span style="background:rgba(255,255,255,0.2);padding:4px 16px;border-radius:20px;font-size:13px;text-transform:uppercase;letter-spacing:1px;">{bid_status}</span>
        <p style="margin:8px 0 0 0;font-size:13px;opacity:0.85;">{date_display}</p>
      </div>
    </div>
  </div>

  <!-- Body -->
  <div style="padding:32px 40px;">

    <!-- Title & Description -->
    <h2 style="margin:0 0 8px 0;font-size:22px;color:#1e3a5f;">{title}</h2>
    {'<p style="margin:0 0 24px 0;color:#4b5563;line-height:1.6;">' + description + '</p>' if description else '<div style="margin-bottom:24px;"></div>'}

    <!-- Customer Info -->
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:24px;padding:16px;background:#f3f4f6;border-radius:6px;">
      {customer_block}
    </div>

    <!-- Line Items -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;width:40px;">#</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Description</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Qty</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Unit Price</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Total</th>
        </tr>
      </thead>
      <tbody>
        {items_rows}
      </tbody>
    </table>

    <!-- Totals -->
    <div style="display:flex;justify-content:flex-end;margin-bottom:32px;">
      <div style="width:280px;">
        <div style="display:flex;justify-content:space-between;padding:6px 0;color:#4b5563;">
          <span>Subtotal</span><span>${subtotal:,.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;color:#4b5563;">
          <span>Tax</span><span>${tax:,.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0;margin-top:4px;border-top:2px solid #1e3a5f;font-size:18px;font-weight:700;color:#1e3a5f;">
          <span>Total</span><span>${total:,.2f}</span>
        </div>
      </div>
    </div>

    <!-- Terms / Timeline / Warranty -->
    {terms_section}
    {timeline_section}
    {warranty_section}

  </div>

  <!-- Footer -->
  <div style="padding:16px 40px;background:#f9fafb;border-top:1px solid #e5e7eb;text-align:center;">
    <p style="margin:0;font-size:12px;color:#9ca3af;">Generated by {biz_name} via AgentNexLiFy</p>
  </div>

</div>

<!-- Print button (hidden in print) -->
<div class="no-print" style="text-align:center;padding:16px;">
  <button onclick="window.print()" style="background:#2563eb;color:#fff;border:none;padding:10px 32px;border-radius:6px;font-size:14px;cursor:pointer;">Print / Save as PDF</button>
</div>

</body>
</html>"""
    return html


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
        logger.exception("Failed to fetch bid %s for PDF generation", bid_id)
        raise HTTPException(status_code=500, detail="Failed to fetch bid")

    if not bid_result.data:
        raise HTTPException(status_code=404, detail="Bid not found")

    bid = bid_result.data[0]

    # Fetch business info
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

    html = _build_bid_html(bid, business, customer)

    # Save the URL pattern to the bid's pdf_url field
    pdf_url = f"/api/v1/bids/{tenant_id}/{bid_id}/pdf"
    try:
        db.table("bids").update({"pdf_url": pdf_url}).eq("id", bid_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.warning("Could not save pdf_url for bid %s", bid_id, exc_info=True)

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="bid-{bid_id[:8]}.html"'},
    )
