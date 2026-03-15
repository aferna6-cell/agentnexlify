"""Reviews management endpoints — Reputation Manager module."""

import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

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

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()

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

    result = db.table("reviews").insert(payload).execute()
    return result.data[0] if result.data else payload


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

    db = get_supabase()
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

    db = get_supabase()
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
async def generate_ai_draft(
    tenant_id: str,
    review_id: str,
    req: AIDraftRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate an AI draft response for a review using Claude."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
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
    business_type = tenant_result.data[0].get("business_type", "") if tenant_result.data else ""

    tone_desc = {
        "professional": "professional and courteous",
        "friendly": "warm and friendly, like talking to a neighbor",
        "casual": "casual and personable",
    }.get(req.tone, "professional and courteous")

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.7,
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
        )
        draft = resp.content[0].text.strip()
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
