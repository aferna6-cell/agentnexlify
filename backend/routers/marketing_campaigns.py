"""Marketing Campaigns endpoints — email/SMS blast campaigns with AI generation."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import anthropic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.dependencies import get_business_context, verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.llm_runtime import call_claude_messages
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/campaigns", tags=["marketing-campaigns"])

VALID_CAMPAIGN_TYPES = {"email", "sms"}
VALID_CAMPAIGN_STATUSES = {"draft", "scheduled", "sending", "sent", "failed"}
VALID_CAMPAIGN_CONTENT_TYPES = {
    "promotional",
    "newsletter",
    "announcement",
    "follow_up",
    "seasonal",
}
MAX_RECIPIENTS_PER_BLAST = 500


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


# --- Helpers ---


def _parse_generated_email(raw: str) -> tuple[str, str]:
    """Parse generated campaign email output into subject/body."""
    subject = ""
    body = raw

    if "SUBJECT:" in raw:
        lines = raw.split("\n", 1)
        first_line = lines[0].strip()
        if first_line.upper().startswith("SUBJECT:"):
            subject = first_line.split(":", 1)[1].strip()
            rest = lines[1] if len(lines) > 1 else ""
            stripped_rest = rest.strip()
            if stripped_rest.startswith("---"):
                body = stripped_rest[3:].strip()
            else:
                body = stripped_rest

    return subject, body


def _validate_campaign_type(campaign_type: str) -> None:
    if campaign_type not in VALID_CAMPAIGN_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid campaign type: {campaign_type}. Must be one of: {', '.join(sorted(VALID_CAMPAIGN_TYPES))}",
        )


def _query_target_leads(db, tenant_id: str, target_filter: dict | None) -> list[dict]:
    """Query leads matching the campaign target filter.

    NOTE: leads table uses client_id, not tenant_id.
    """
    query = (
        db.table("leads")
        .select("id, name, email, phone, status, tags, lead_temperature")
        .eq("client_id", tenant_id)
        .eq("unsubscribed", False)
        .order("created_at", desc=True)
        .limit(MAX_RECIPIENTS_PER_BLAST)
    )

    if target_filter:
        if target_filter.get("status"):
            # Filter by any of the specified statuses
            query = query.in_("status", target_filter["status"])
        if target_filter.get("lead_temperature"):
            query = query.in_("lead_temperature", target_filter["lead_temperature"])
        # Tags filtering is done post-query since it requires array overlap

    try:
        result = query.execute()
        leads = result.data or []
    except Exception:
        logger.exception("Failed to query target leads for tenant %s", tenant_id)
        return []

    # Post-filter by tags if specified (array overlap)
    if target_filter and target_filter.get("tags"):
        target_tags = set(target_filter["tags"])
        leads = [
            lead
            for lead in leads
            if lead.get("tags") and set(lead["tags"]) & target_tags
        ]

    return leads


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
        db = get_supabase()
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
        db = get_supabase()
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

        # Total count
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
        db = get_supabase()
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

    # Validate status if provided — block reverting sent/sending campaigns to draft
    if req.status:
        if req.status not in VALID_CAMPAIGN_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
        if req.status in ("sent", "sending"):
            raise HTTPException(
                status_code=400, detail="Cannot manually set status to sent/sending"
            )

    updates = {}
    for k, v in req.model_dump().items():
        if v is not None:
            updates[k] = v

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        db = get_supabase()
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
        db = get_supabase()
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


async def _send_campaign_background(
    campaign_id: str,
    tenant_id: str,
    leads: list[dict],
    campaign: dict,
) -> None:
    """Background task: send a campaign to all matched leads and update DB with results.

    Runs after the HTTP handler has already returned. On any unhandled error the
    campaign status is set to 'failed' so the dashboard never shows a stuck 'sending'
    state.
    """
    try:
        db = get_supabase()
        total_sent = 0
        total_failed = 0
        campaign_type = campaign["type"]
        campaign_send_records = []

        for i, lead in enumerate(leads):
            lead_id = lead["id"]
            send_status = "failed"
            recipient = ""

            # Yield control every 10 sends to prevent event loop starvation
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(0)

            try:
                if campaign_type == "email":
                    recipient = lead.get("email", "")
                    if not recipient:
                        continue

                    unsub_url = build_unsubscribe_url(lead_id, tenant_id)
                    result = await send_email(
                        to=recipient,
                        subject=campaign.get("subject", ""),
                        body_html=campaign["body"],
                        tenant_id=tenant_id,
                        unsubscribe_url=unsub_url,
                        lead_id=lead_id,
                    )
                    if result.get("success"):
                        send_status = "sent"
                        total_sent += 1
                    else:
                        total_failed += 1
                        logger.warning(
                            "Campaign email failed for lead %s: %s",
                            lead_id,
                            result.get("detail"),
                        )

                elif campaign_type == "sms":
                    recipient = lead.get("phone", "")
                    if not recipient:
                        continue

                    success = await send_sms(to=recipient, body=campaign["body"])
                    if success:
                        send_status = "sent"
                        total_sent += 1
                    else:
                        total_failed += 1
                        logger.warning("Campaign SMS failed for lead %s", lead_id)

            except Exception:
                total_failed += 1
                logger.exception("Failed to send campaign to lead %s", lead_id)

            # Collect the send record for batch insert
            campaign_send_records.append(
                {
                    "campaign_id": campaign_id,
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "channel": campaign_type,
                    "recipient": recipient,
                    "status": send_status,
                }
            )

        # Batch-insert all campaign_sends at once (avoids N+1 queries)
        if campaign_send_records:
            try:
                db.table("campaign_sends").insert(campaign_send_records).execute()
            except Exception:
                logger.exception(
                    "Failed to batch-insert campaign sends for campaign %s", campaign_id
                )

        # Update campaign with final results
        final_status = "sent" if total_sent > 0 else "failed"
        try:
            db.table("marketing_campaigns").update(
                {
                    "status": final_status,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "total_recipients": len(leads),
                    "total_sent": total_sent,
                }
            ).eq("id", campaign_id).execute()
            logger.info(
                "Campaign %s completed: status=%s sent=%d failed=%d",
                campaign_id,
                final_status,
                total_sent,
                total_failed,
            )
        except Exception:
            logger.exception(
                "Failed to update final status for campaign %s (sent=%d, failed=%d)",
                campaign_id,
                total_sent,
                total_failed,
            )

    except Exception:
        logger.exception(
            "Unhandled error in background send for campaign %s — marking as failed",
            campaign_id,
        )
        try:
            db_bg = get_supabase()
            db_bg.table("marketing_campaigns").update(
                {
                    "status": "failed",
                }
            ).eq("id", campaign_id).execute()
        except Exception:
            logger.exception(
                "Failed to mark campaign %s as failed after background error",
                campaign_id,
            )


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

    try:
        db = get_supabase()

        # Fetch the campaign
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

        # Query target leads (uses client_id, not tenant_id) before changing status
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

        # Mark as sending with a timestamp before dispatching the background task
        # Use conditional update to prevent race conditions (double-send)
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

        # Dispatch the send loop as a non-blocking background task and return immediately
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
            db = get_supabase()
            db.table("marketing_campaigns").update(
                {
                    "status": "failed",
                }
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
        db = get_supabase()

        # Verify campaign belongs to tenant
        campaign_result = (
            db.table("marketing_campaigns")
            .select(
                "id, name, type, status, total_recipients, total_sent, total_opened, total_clicked, sent_at"
            )
            .eq("id", campaign_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not campaign_result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = campaign_result.data[0]

        # Get send-level analytics
        sends_result = (
            db.table("campaign_sends")
            .select("id, status, sent_at, opened_at, clicked_at")
            .eq("campaign_id", campaign_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        sends = sends_result.data or []

        by_status = {}
        for send in sends:
            s = send["status"]
            by_status[s] = by_status.get(s, 0) + 1

        total_sent = campaign.get("total_sent", 0)
        total_opened = by_status.get("opened", 0) + by_status.get("clicked", 0)
        total_clicked = by_status.get("clicked", 0)

        open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0
        click_rate = (
            round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0
        )

        trend_data = []
        if campaign.get("sent_at"):
            try:
                sent_date = datetime.fromisoformat(
                    campaign["sent_at"].replace("Z", "+00:00")
                )
                days_since_sent = (datetime.now(timezone.utc) - sent_date).days
                lookback = min(days_since_sent, 30)
                if lookback > 0:
                    trend_start = (
                        (datetime.now(timezone.utc) - timedelta(days=lookback))
                        .date()
                        .isoformat()
                    )
                    email_events_result = (
                        db.table("email_events")
                        .select("event_type, created_at")
                        .eq("campaign_tag", campaign_id)
                        .eq("tenant_id", tenant_id)
                        .gte("created_at", trend_start)
                        .execute()
                    )
                    events = email_events_result.data or []
                    date_event_map: dict[str, dict] = {}
                    for evt in events:
                        date_key = evt.get("created_at", "")[:10]
                        if date_key not in date_event_map:
                            date_event_map[date_key] = {"opens": 0, "clicks": 0}
                        if evt.get("event_type") == "open":
                            date_event_map[date_key]["opens"] += 1
                        elif evt.get("event_type") == "click":
                            date_event_map[date_key]["clicks"] += 1

                    for i in range(lookback + 1):
                        date = (
                            datetime.now(timezone.utc).date() - timedelta(days=i)
                        ).isoformat()
                        data = date_event_map.get(date, {"opens": 0, "clicks": 0})
                        trend_data.append(
                            {
                                "date": date,
                                "opens": data["opens"],
                                "clicks": data["clicks"],
                            }
                        )
                    trend_data.reverse()
            except Exception:
                logger.warning("Failed to load trend data for campaign %s", campaign_id, exc_info=True)

        device_breakdown = {}
        try:
            email_events_result = (
                db.table("email_events")
                .select("details")
                .eq("campaign_tag", campaign_id)
                .eq("tenant_id", tenant_id)
                .limit(500)
                .execute()
            )
            for evt in email_events_result.data or []:
                details = evt.get("details") or {}
                device = details.get("device") or details.get("user_agent", "unknown")
                if "iPhone" in device or "Android" in device:
                    device_breakdown["mobile"] = device_breakdown.get("mobile", 0) + 1
                elif "Desktop" in device or "computer" in device.lower():
                    device_breakdown["desktop"] = device_breakdown.get("desktop", 0) + 1
                else:
                    device_breakdown["other"] = device_breakdown.get("other", 0) + 1
        except Exception:
            logger.warning("Failed to load device breakdown for campaign %s", campaign_id, exc_info=True)

        return {
            "campaign": campaign,
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_bounced": by_status.get("bounced", 0),
            "total_failed": by_status.get("failed", 0),
            "open_rate": open_rate,
            "click_rate": click_rate,
            "by_status": by_status,
            "trend_data": trend_data,
            "device_breakdown": device_breakdown,
        }
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
        db = get_supabase()
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

    db = get_supabase()
    business_name, business_type = get_business_context(db, tenant_id)
    biz_context = f" for {business_name}" + (
        f", a {business_type}" if business_type else ""
    )

    type_instructions = {
        "promotional": "Create a compelling promotional email that highlights a special offer or service. Include urgency and a clear call to action.",
        "newsletter": "Create an engaging newsletter that provides value through tips, updates, or industry insights. Keep it informative and helpful.",
        "announcement": "Create a professional announcement email about something new or noteworthy. Build excitement while being clear and concise.",
        "follow_up": "Create a warm follow-up email that re-engages leads who haven't responded. Be friendly, not pushy. Reference their earlier interest.",
        "seasonal": "Create a seasonal or holiday-themed email that ties the business to current events or seasons. Be festive but professional.",
    }

    try:
        resp = await call_claude_messages(
            operation="marketing_campaigns.generate_email",
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.7,
            timeout=30.0,
            system=(
                f"You are an email marketing expert creating campaign emails{biz_context}. "
                f"{type_instructions.get(req.campaign_type, '')} "
                f"Tone: {req.tone}.\n\n"
                "Return the email in this exact format:\n"
                "SUBJECT: [the email subject line]\n"
                "---\n"
                "[the email body in HTML format with proper tags like <h2>, <p>, <a>, etc.]\n\n"
                "The email body should be 150-300 words. Use clean, responsive-friendly HTML. "
                "Include a clear call to action. Do not include <html>, <head>, or <body> tags -- just the inner content."
            ),
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

    # Parse subject and body
    subject, body = _parse_generated_email(raw)

    return {
        "subject": subject,
        "body": body,
        "campaign_type": req.campaign_type,
        "tone": req.tone,
    }
