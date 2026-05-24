"""Static-path bid routes — list, create, stats, templates, AI generation.

Endpoints registered under `/api/v1/bids` (handled in aggregator).
All routes here use only `{tenant_id}` or static path segments — they MUST be
included BEFORE `bids_dynamic.py` to avoid `/{tenant_id}/{bid_id}` shadowing.
"""

import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.routers.bids_models import (
    AIBidGenerateRequest,
    BidCreate,
    BidTemplateCreate,
    _verify_tenant,
    logger,
)
from backend.services.bid_rendering import (
    build_ai_bid_prompt,
    build_business_context,
    compute_totals,
    parse_ai_bid_response,
)
from backend.services.llm_runtime import call_claude_messages

router = APIRouter()


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

    db = get_service_supabase()
    try:
        query = (
            db.table("bids")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("status", status)
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
    subtotal, tax, total = compute_totals(items)

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

    db = get_service_supabase()
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

    db = get_service_supabase()
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

    sent_or_decided = [
        b for b in bids if b.get("status") in ("sent", "viewed", "accepted", "rejected", "expired")
    ]
    accepted_count = sum(1 for b in bids if b.get("status") == "accepted")
    win_rate = round(accepted_count / len(sent_or_decided) * 100, 1) if sent_or_decided else 0.0

    all_totals = [float(b.get("total", 0)) for b in bids]
    avg_value = round(sum(all_totals) / len(all_totals), 2) if all_totals else 0.0

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

    db = get_service_supabase()
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

    db = get_service_supabase()
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

    db = get_service_supabase()
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

    db = get_service_supabase()
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
            biz_type = tenant_result.data[0].get("business_type") or ""
            city = tenant_result.data[0].get("city") or ""
    except Exception:
        logger.warning("Could not fetch tenant info for AI bid generation", exc_info=True)

    context = build_business_context(biz_name, biz_type, city)
    prompt = build_ai_bid_prompt(req.job_description, context)

    text = ""
    try:
        response = await call_claude_messages(
            operation="bids.ai_generate",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            timeout=30.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"tenant_id": tenant_id, "has_business_context": bool(context.strip())},
        )
        text = response.text
        return parse_ai_bid_response(text)
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
