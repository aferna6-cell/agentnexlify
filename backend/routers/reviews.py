"""Reviews management endpoints — Reputation Manager module."""

import html as html_mod
import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.dependencies import _get_current_tenant
from backend.services.email_sender import send_email, build_unsubscribe_url
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ReviewResponseStats(BaseModel):
    total_reviews: int = 0
    responded_count: int = 0
    unresponded_count: int = 0
    response_rate_percent: float = 0.0
    avg_response_time_hours: float | None = None
    reviews_this_month: int = 0
    responses_this_month: int = 0


class ReviewCreate(BaseModel):
    platform: str = "google"
    author_name: str
    rating: int = Field(..., ge=1, le=5)
    review_text: str | None = None
    review_date: str | None = None
    external_review_id: str | None = None


class ReviewUpdate(BaseModel):
    owner_response: str | None = None
    ai_draft_response: str | None = None
    responded: bool | None = None


class AIDraftRequest(BaseModel):
    tone: str = "professional"  # professional, friendly, casual


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}")
async def list_reviews(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    platform: str | None = Query(None),
    rating: int | None = Query(None, ge=1, le=5),
    responded: bool | None = Query(None),
):
    """List reviews with optional filters."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    query = (
        db.table("reviews")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("review_date", desc=True)
    )

    if platform:
        query = query.eq("platform", platform)
    if rating is not None:
        query = query.eq("rating", rating)
    if responded is not None:
        query = query.eq("responded", responded)

    result = query.execute()
    reviews = result.data or []

    # Compute summary stats
    total = len(reviews)
    avg_rating = round(sum(r["rating"] for r in reviews) / total, 1) if total else 0
    responded_count = sum(1 for r in reviews if r.get("responded"))

    return {
        "reviews": reviews,
        "stats": {
            "total": total,
            "average_rating": avg_rating,
            "responded": responded_count,
            "unresponded": total - responded_count,
        },
    }


@router.get("/{tenant_id}/response-stats", response_model=ReviewResponseStats)
async def get_response_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return response history stats for a tenant's reviews.

    Includes total/responded/unresponded counts, response rate, approximate
    average response time (using updated_at as proxy for response time), and
    this-month breakdowns.
    """
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    stats = ReviewResponseStats()

    try:
        all_reviews = (
            db.table("reviews")
            .select("id, responded, created_at, updated_at, review_date")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        reviews = all_reviews.data or []
    except Exception:
        logger.error("Failed to fetch reviews for response stats, tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch review stats")

    if not reviews:
        return stats

    stats.total_reviews = len(reviews)
    stats.responded_count = sum(1 for r in reviews if r.get("responded"))
    stats.unresponded_count = stats.total_reviews - stats.responded_count
    stats.response_rate_percent = round(
        (stats.responded_count / stats.total_reviews) * 100, 1
    )

    # Approximate avg response time: time between created_at and updated_at
    # for responded reviews. updated_at is set when owner_response is written.
    response_times_hours: list[float] = []
    for r in reviews:
        if not r.get("responded"):
            continue
        created_raw = r.get("review_date") or r.get("created_at")
        updated_raw = r.get("updated_at")
        if not created_raw or not updated_raw:
            continue
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            updated_dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
            diff_hours = (updated_dt - created_dt).total_seconds() / 3600
            if diff_hours >= 0:
                response_times_hours.append(diff_hours)
        except Exception:
            logger.debug("Skipping review %s for response time calc", r.get("id"))

    if response_times_hours:
        stats.avg_response_time_hours = round(
            sum(response_times_hours) / len(response_times_hours), 1
        )

    # This-month breakdowns
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for r in reviews:
        created_raw = r.get("created_at") or r.get("review_date")
        if not created_raw:
            continue
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        if created_dt >= month_start:
            stats.reviews_this_month += 1
            if r.get("responded"):
                stats.responses_this_month += 1

    return stats


@router.post("/{tenant_id}")
async def create_review(
    tenant_id: str,
    req: ReviewCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Manually add a review (for platforms without API integration)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Dedup by external_review_id if provided
    if req.external_review_id:
        existing = (
            db.table("reviews")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("external_review_id", req.external_review_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]

    payload = {
        "tenant_id": tenant_id,
        "platform": req.platform,
        "author_name": req.author_name,
        "rating": req.rating,
        "review_text": req.review_text,
        "review_date": req.review_date or datetime.now(timezone.utc).isoformat(),
        "external_review_id": req.external_review_id,
    }

    try:
        result = db.table("reviews").insert(payload).execute()
    except Exception:
        logger.exception("Failed to insert review for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create review")

    review = result.data[0] if result.data else payload
    try:
        fire_event_background(tenant_id, "review.received", {
            "review_id": review.get("id"),
            "platform": req.platform,
            "author_name": req.author_name,
            "rating": req.rating,
        })
    except Exception:
        logger.warning("Failed to fire review.received webhook for tenant %s", tenant_id, exc_info=True)
    return review


@router.patch("/{tenant_id}/{review_id}")
async def update_review(
    tenant_id: str,
    review_id: str,
    req: ReviewUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a review (add response, mark as responded)."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If setting owner_response, also mark as responded
    if "owner_response" in updates and updates["owner_response"]:
        updates["responded"] = True

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_service_supabase()
    result = (
        db.table("reviews")
        .update(updates)
        .eq("id", review_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    return result.data[0]


@router.delete("/{tenant_id}/{review_id}", status_code=204)
async def delete_review(
    tenant_id: str,
    review_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a review."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("reviews")
        .delete()
        .eq("id", review_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")


@router.post("/{tenant_id}/{review_id}/ai-draft")
@limiter.limit("10/minute")
async def generate_ai_draft(
    request: Request,
    tenant_id: str,
    review_id: str,
    req: AIDraftRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate an AI draft response for a review using Claude."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    review_result = (
        db.table("reviews")
        .select("*")
        .eq("id", review_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not review_result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    review = review_result.data[0]

    # Get business name for context
    tenant_result = (
        db.table("tenants")
        .select("business_name, business_type")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    business_name = tenant_result.data[0]["business_name"] if tenant_result.data else "our business"
    business_type = (tenant_result.data[0].get("business_type") or "") if tenant_result.data else ""

    tone_desc = {
        "professional": "professional and courteous",
        "friendly": "warm and friendly, like talking to a neighbor",
        "casual": "casual and personable",
    }.get(req.tone, "professional and courteous")

    try:
        resp = await call_claude_messages(
            operation="reviews.generate_draft",
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.7,
            timeout=30.0,
            system=(
                f"You are writing a review response for {business_name}"
                f"{f', a {business_type}' if business_type else ''}. "
                f"Tone: {tone_desc}. "
                "Keep it concise (2-4 sentences). "
                "Thank the reviewer by name. "
                "If the review is positive, express gratitude and invite them back. "
                "If negative, apologize sincerely, acknowledge the issue, and offer to make it right. "
                "Never be defensive. Never use generic templates. Make it personal."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Review from {review['author_name']} "
                    f"({review['rating']}/5 stars):\n\n"
                    f"{review.get('review_text', 'No text provided')}"
                ),
            }],
            metadata={"tenant_id": tenant_id, "review_id": review_id, "tone": req.tone},
        )
        draft = resp.text.strip()
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited — please try again in a moment")
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during review draft")
        raise HTTPException(status_code=502, detail="AI service configuration error")
    except anthropic.APIError as e:
        logger.error("Anthropic API error during review draft: %s", str(e))
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")
    except Exception:
        logger.error("AI draft generation failed for review %s", review_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate AI draft")

    # Save the draft
    db.table("reviews").update({
        "ai_draft_response": draft,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", review_id).execute()

    return {"draft": draft}


@router.post("/{tenant_id}/request-review/{lead_id}")
@limiter.limit("10/minute")
async def send_review_request(
    request: Request,
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Send a one-click review request to a specific lead via email and/or SMS."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

    # Load lead
    lead_result = db.table("leads").select("name, email, phone, unsubscribed").eq("id", lead_id).eq("client_id", tenant_id).limit(1).execute()
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = lead_result.data[0]

    if lead.get("unsubscribed"):
        raise HTTPException(status_code=400, detail="Lead has unsubscribed from communications")

    if not lead.get("email") and not lead.get("phone"):
        raise HTTPException(status_code=400, detail="Lead has no email or phone number")

    # Load tenant for business name + review link
    tenant_result = db.table("tenants").select("business_name, google_review_link, google_place_id").eq("id", tenant_id).limit(1).execute()
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = tenant_result.data[0]

    # Build review link
    place_id = tenant.get("google_place_id")
    if place_id:
        review_link = f"https://search.google.com/local/writereview?placeid={place_id}"
    else:
        review_link = tenant.get("google_review_link") or ""

    if not review_link:
        raise HTTPException(status_code=400, detail="No review link configured — add your Google review link in Settings")

    business_name = tenant.get("business_name") or "Our Team"
    customer_name = lead.get("name") or "there"
    sent_channels = []

    # Send email
    if lead.get("email"):
        unsub_url = build_unsubscribe_url(lead_id, tenant_id)
        safe_name = html_mod.escape(customer_name)
        safe_biz = html_mod.escape(business_name)
        subject = f"How was your experience with {business_name}?"
        body = (
            f"<h2>Hi {safe_name},</h2>"
            f"<p>Thank you for choosing <strong>{safe_biz}</strong>! "
            f"We hope everything went well.</p>"
            f"<p>We'd really appreciate it if you could take a moment to share your experience:</p>"
            f'<p style="text-align:center;margin:20px 0;">'
            f'<a href="{review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
            f'border-radius:6px;text-decoration:none;font-weight:600;">Leave a Review</a></p>'
            f"<p>Your feedback helps us improve and helps others find us. Thank you!</p>"
            f"<p>Best,<br>The {safe_biz} Team</p>"
        )
        try:
            result = await send_email(to=lead["email"], subject=subject, body_html=body, tenant_id=tenant_id, unsubscribe_url=unsub_url)
            if result.get("success"):
                sent_channels.append("email")
        except Exception:
            logger.exception("Failed to send review request email to lead %s", lead_id)

    # Send SMS
    if lead.get("phone"):
        sms_body = (
            f"Hi {customer_name}, thanks for choosing {business_name}! "
            f"We'd love your feedback. Leave a review here: {review_link}"
        )
        try:
            sms_ok = await send_sms(to=lead["phone"], body=sms_body)
            if sms_ok:
                sent_channels.append("sms")
        except Exception:
            logger.exception("Failed to send review request SMS to lead %s", lead_id)

    if not sent_channels:
        raise HTTPException(status_code=500, detail="Failed to send review request")

    # Log the activity
    try:
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "activity_type": "review_request_sent",
            "description": f"Review request sent via {', '.join(sent_channels)}",
        }).execute()
    except Exception:
        logger.warning("Failed to log review request activity for lead %s", lead_id, exc_info=True)

    return {"sent_via": sent_channels}
