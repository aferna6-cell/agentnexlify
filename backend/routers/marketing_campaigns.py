"""Marketing Campaigns endpoints — email/SMS blast campaigns with AI generation.

Aggregation, recipient queries, analytics, and AI prompt scaffolding live in
`backend/services/marketing_campaigns_service.py`. This module owns auth,
HTTP shape, and the campaign send orchestration (background-task dispatch +
status transitions).
"""

import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.dependencies import _get_current_tenant, get_business_context, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.addon_gate import require_marketing_addon
from backend.services.campaign_service import _send_campaign_background
from backend.services.llm_runtime import call_claude_messages
from backend.services.marketing_campaigns_service import (
    VALID_CAMPAIGN_CONTENT_TYPES,
    VALID_CAMPAIGN_STATUSES,
    VALID_CAMPAIGN_TYPES,
    CampaignNotFound,
    build_email_system_prompt,
    compute_campaign_analytics,
    parse_generated_email,
    query_target_leads,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["marketing-campaigns"],
    dependencies=[Depends(require_marketing_addon)],
)


# --- Pydantic Models ---


class CampaignTargetFilter(BaseModel):
    status: list[str] | None = None
    tags: list[str] | None = None
    lead_temperature: list[str] | None = None


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="email or sms")
    subject: str | None = Field(None, max_length=200)
    body: str = Field(..., min_length=1, max_length=50000)
    target_filter: CampaignTargetFilter | None = None
    scheduled_for: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    subject: str | None = Field(None, max_length=200)
    body: str | None = Field(None, max_length=50000)
    target_filter: CampaignTargetFilter | None = None
    scheduled_for: str | None = None
    status: str | None = Field(None, max_length=20)


class GenerateEmailRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=1000)
    tone: str = Field("professional", max_length=100)
    campaign_type: str = Field(
        "promotional",
        description="promotional, newsletter, announcement, follow_up, seasonal",
    )


def _validate_campaign_type(campaign_type: str) -> None:
    if campaign_type not in VALID_CAMPAIGN_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid campaign type: {campaign_type}. Must be one of: {', '.join(sorted(VALID_CAMPAIGN_TYPES))}",
        )


# Back-compat aliases — tests import/patch these at the router path.
_parse_generated_email = parse_generated_email
_query_target_leads = query_target_leads


# --- Campaign CRUD ---


@router.post("/{tenant_id}")
async def create_campaign(
    tenant_id: str,
    req: CampaignCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a marketing campaign."""
    verify_tenant(claims, tenant_id)
    _validate_campaign_type(req.type)

    if req.type == "email" and not req.subject:
        raise HTTPException(
            status_code=400, detail="Email campaigns require a subject line"
        )

    payload = {
        "tenant_id": tenant_id,
        "name": req.name,
        "type": req.type,
        "subject": req.subject,
        "body": req.body,
        "target_filter": req.target_filter.model_dump() if req.target_filter else {},
        "status": "scheduled" if req.scheduled_for else "draft",
        "scheduled_for": req.scheduled_for,
    }

    try:
        db = get_service_supabase()
        result = db.table("marketing_campaigns").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create campaign")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create campaign for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create campaign")


@router.get("/{tenant_id}")
async def list_campaigns(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
    campaign_type: str | None = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List marketing campaigns with optional filters."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        query = (
            db.table("marketing_campaigns")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if status:
            query = query.eq("status", status)
        if campaign_type:
            query = query.eq("type", campaign_type)

        result = query.execute()
        items = result.data or []

        count_query = (
            db.table("marketing_campaigns")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
        )
        if status:
            count_query = count_query.eq("status", status)
        if campaign_type:
            count_query = count_query.eq("type", campaign_type)
        count_result = count_query.execute()
        total = count_result.count if count_result.count is not None else len(items)

        return {"campaigns": items, "total": total}
    except Exception:
        logger.exception("Failed to list campaigns for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list campaigns")


@router.get("/{tenant_id}/{campaign_id}")
async def get_campaign(
    tenant_id: str,
    campaign_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single campaign with details."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        result = (
            db.table("marketing_campaigns")
            .select("*")
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to get campaign %s for tenant %s", campaign_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to get campaign")


@router.put("/{tenant_id}/{campaign_id}")
async def update_campaign(
    tenant_id: str,
    campaign_id: str,
    req: CampaignUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a marketing campaign."""
    verify_tenant(claims, tenant_id)

    if req.status:
        if req.status not in VALID_CAMPAIGN_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
        if req.status in ("sent", "sending"):
            raise HTTPException(
                status_code=400, detail="Cannot manually set status to sent/sending"
            )

    updates = {k: v for k, v in req.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        db = get_service_supabase()
        result = (
            db.table("marketing_campaigns")
            .update(updates)
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to update campaign %s for tenant %s", campaign_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to update campaign")


@router.delete("/{tenant_id}/{campaign_id}", status_code=204)
async def delete_campaign(
    tenant_id: str,
    campaign_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a marketing campaign."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        result = (
            db.table("marketing_campaigns")
            .delete()
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to delete campaign %s for tenant %s", campaign_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to delete campaign")


# --- Send Campaign ---


@router.post("/{tenant_id}/{campaign_id}/send")
@limiter.limit("3/minute")
async def send_campaign(
    request: Request,
    tenant_id: str,
    campaign_id: str,
    claims: dict = Depends(_get_current_tenant),
    background_tasks: BackgroundTasks = None,
):
    """Execute/send a marketing campaign to matching leads.

    Validates the campaign, builds the recipient list, marks status as 'sending',
    then returns immediately. The actual send loop runs as an asyncio background task
    so the HTTP handler is never blocked for more than a few milliseconds.
    """
    verify_tenant(claims, tenant_id)

    _PAID_PLANS = {"growth", "professional", "autopilot", "enterprise"}
    tenant_plan = claims.get("plan", "free")
    if tenant_plan not in _PAID_PLANS:
        raise HTTPException(status_code=403, detail="Campaign sending requires a paid plan")

    try:
        db = get_service_supabase()

        campaign_result = (
            db.table("marketing_campaigns")
            .select("*")
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not campaign_result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = campaign_result.data[0]

        if campaign["status"] in ("sending", "sent"):
            raise HTTPException(
                status_code=400, detail=f"Campaign already {campaign['status']}"
            )

        target_filter = campaign.get("target_filter") or {}
        leads = _query_target_leads(db, tenant_id, target_filter)

        if not leads:
            db.table("marketing_campaigns").update(
                {
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "total_recipients": 0,
                    "total_sent": 0,
                }
            ).eq("id", campaign_id).execute()
            return {
                "campaign_id": campaign_id,
                "status": "sent",
                "total_recipients": 0,
                "total_sent": 0,
                "message": "No matching leads found",
            }

        # Conditional update prevents race conditions (double-send).
        status_update = (
            db.table("marketing_campaigns")
            .update(
                {
                    "status": "sending",
                    "sending_started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .in_("status", ["draft", "scheduled"])
            .execute()
        )
        if not status_update.data:
            raise HTTPException(
                status_code=400,
                detail="Campaign is already being sent or in an invalid state",
            )

        background_tasks.add_task(
            _send_campaign_background, campaign_id, tenant_id, leads, campaign
        )

        return {"status": "sending", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to initiate campaign %s for tenant %s", campaign_id, tenant_id
        )
        try:
            db = get_service_supabase()
            db.table("marketing_campaigns").update(
                {"status": "failed"}
            ).eq("id", campaign_id).execute()
        except Exception:
            logger.exception(
                "Failed to mark campaign %s as failed after initiation error",
                campaign_id,
            )
        raise HTTPException(status_code=500, detail="Campaign send failed")


# --- Campaign Analytics ---


@router.get("/{tenant_id}/{campaign_id}/analytics")
async def get_campaign_analytics(
    tenant_id: str,
    campaign_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get campaign performance analytics."""
    verify_tenant(claims, tenant_id)

    try:
        return compute_campaign_analytics(get_service_supabase(), tenant_id, campaign_id)
    except CampaignNotFound:
        raise HTTPException(status_code=404, detail="Campaign not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get analytics for campaign %s", campaign_id)
        raise HTTPException(status_code=500, detail="Failed to load campaign analytics")


# --- Recipient Estimate ---


@router.post("/{tenant_id}/estimate")
async def estimate_recipients(
    tenant_id: str,
    body: CampaignTargetFilter,
    claims: dict = Depends(_get_current_tenant),
):
    """Estimate how many leads match the given target filter."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        leads = _query_target_leads(db, tenant_id, body.model_dump() if body else None)
        return {"estimated_recipients": len(leads)}
    except Exception:
        logger.exception("Failed to estimate recipients for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to estimate recipients")


# --- AI Email Generation ---


@router.post("/{tenant_id}/generate-email")
@limiter.limit("10/minute")
async def generate_campaign_email(
    request: Request,
    tenant_id: str,
    req: GenerateEmailRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI-generate a campaign email with subject and body."""
    verify_tenant(claims, tenant_id)

    if req.campaign_type not in VALID_CAMPAIGN_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid campaign_type. Must be one of: {', '.join(sorted(VALID_CAMPAIGN_CONTENT_TYPES))}",
        )

    db = get_service_supabase()
    business_name, business_type = get_business_context(db, tenant_id)
    system_prompt = build_email_system_prompt(
        business_name, business_type, req.campaign_type, req.tone
    )

    try:
        resp = await call_claude_messages(
            operation="marketing_campaigns.generate_email",
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.7,
            timeout=30.0,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Topic: {req.topic}\nCampaign type: {req.campaign_type}",
                }
            ],
            metadata={
                "tenant_id": tenant_id,
                "campaign_type": req.campaign_type,
                "tone": req.tone,
            },
        )
        raw = resp.text.strip()
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI service rate limited -- please try again in a moment",
        )
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during email generation")
        raise HTTPException(status_code=502, detail="AI service configuration error")
    except anthropic.APIError as e:
        logger.error("Anthropic API error during email generation: %s", str(e))
        raise HTTPException(
            status_code=502, detail="AI service temporarily unavailable"
        )
    except Exception:
        logger.exception("Campaign email AI generation failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="AI email generation failed")

    subject, body = parse_generated_email(raw)

    return {
        "subject": subject,
        "body": body,
        "campaign_type": req.campaign_type,
        "tone": req.tone,
    }
