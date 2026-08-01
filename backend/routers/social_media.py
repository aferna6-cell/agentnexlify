"""Social Media Marketing endpoints — post management, AI content generation, calendar, analytics."""

import logging
from datetime import datetime, timedelta, timezone
from calendar import monthrange

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, get_business_context, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.plan_gate import require_marketing_access
from backend.services.llm_runtime import call_claude_messages
from backend.services.social_media_images import SocialImageGenError, generate_post_image
from backend.services.social_media_ai import (
    PLATFORM_LIMITS,
    VALID_PLATFORMS,
    VALID_STATUSES,
    build_campaign_system_prompt,
    build_post_system_prompt,
    parse_generated_campaign_posts,
    parse_post_response,
    validate_platform as _validate_platform,
    validate_status as _validate_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/social",
    tags=["social-media"],
    dependencies=[Depends(require_marketing_access)],
)

# Re-export for tests that import from the router module (Rule 10: never change tests).
_parse_generated_campaign_posts = parse_generated_campaign_posts

__all__ = [
    "router",
    "VALID_PLATFORMS",
    "VALID_STATUSES",
    "PLATFORM_LIMITS",
    "_parse_generated_campaign_posts",
    "AIGenerateRequest",
    "AICampaignRequest",
    "SocialPostCreate",
    "SocialPostUpdate",
    "generate_post_content",
    "generate_campaign_content",
]


# --- Pydantic Models ---

class SocialPostCreate(BaseModel):
    platform: str = Field(..., description="Target platform")
    content: str = Field(..., min_length=1, max_length=5000)
    media_urls: list[str] | None = None
    scheduled_for: str | None = None
    hashtags: list[str] | None = None


class SocialPostUpdate(BaseModel):
    platform: str | None = Field(None, max_length=50)
    content: str | None = Field(None, max_length=5000)
    media_urls: list[str] | None = Field(None, max_length=20)
    scheduled_for: str | None = None
    hashtags: list[str] | None = Field(None, max_length=30)
    status: str | None = Field(None, max_length=20)


class AIGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=1000)
    platform: str = Field(..., description="Target platform")
    tone: str | None = Field(None, max_length=100)
    include_hashtags: bool = True


class AICampaignRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=1000)
    platforms: list[str] = Field(..., min_length=1, max_length=5)
    posts_per_week: int = Field(7, ge=1, le=21)


class SocialImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    platform: str = Field(..., description="Target platform — controls output image size")
    post_id: str | None = Field(None, description="If set, append the generated URL to this post's media_urls")


class SocialImageGenerateResponse(BaseModel):
    url: str
    width: int
    height: int


# --- Post CRUD Endpoints ---

@router.post("/{tenant_id}/posts")
async def create_post(
    tenant_id: str,
    req: SocialPostCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a social media post."""
    verify_tenant(claims, tenant_id)
    _validate_platform(req.platform)

    status = "scheduled" if req.scheduled_for else "draft"

    payload = {
        "tenant_id": tenant_id,
        "platform": req.platform,
        "content": req.content,
        "media_urls": req.media_urls or [],
        "hashtags": req.hashtags or [],
        "status": status,
        "scheduled_for": req.scheduled_for,
    }

    try:
        db = get_service_supabase()
        result = db.table("social_posts").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create post")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create social post for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create social post")


@router.get("/{tenant_id}/posts")
async def list_posts(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List social media posts with optional filters."""
    verify_tenant(claims, tenant_id)

    if platform:
        _validate_platform(platform)
    if status:
        _validate_status(status)

    try:
        db = get_service_supabase()
        query = (
            db.table("social_posts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if platform:
            query = query.eq("platform", platform)
        if status:
            query = query.eq("status", status)
        if date_from:
            query = query.gte("created_at", f"{date_from}T00:00:00Z")
        if date_to:
            query = query.lte("created_at", f"{date_to}T23:59:59Z")

        result = query.execute()
        items = result.data or []

        count_query = (
            db.table("social_posts")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
        )
        if platform:
            count_query = count_query.eq("platform", platform)
        if status:
            count_query = count_query.eq("status", status)
        count_result = count_query.execute()
        total = count_result.count if count_result.count is not None else len(items)

        return {"posts": items, "total": total}
    except Exception:
        logger.exception("Failed to list social posts for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list posts")


@router.put("/{tenant_id}/posts/{post_id}")
async def update_post(
    tenant_id: str,
    post_id: str,
    req: SocialPostUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a social media post."""
    verify_tenant(claims, tenant_id)

    if req.platform:
        _validate_platform(req.platform)
    if req.status:
        _validate_status(req.status)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        db = get_service_supabase()
        result = (
            db.table("social_posts")
            .update(updates)
            .eq("id", post_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update social post %s for tenant %s", post_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update post")


@router.delete("/{tenant_id}/posts/{post_id}", status_code=204)
async def delete_post(
    tenant_id: str,
    post_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a social media post."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        result = (
            db.table("social_posts")
            .delete()
            .eq("id", post_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete social post %s for tenant %s", post_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to delete post")


# --- AI Content Generation ---

@router.post("/{tenant_id}/generate")
async def generate_post_content(
    tenant_id: str,
    req: AIGenerateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI-generate social media content optimized for a specific platform."""
    verify_tenant(claims, tenant_id)
    _validate_platform(req.platform)

    db = get_service_supabase()
    business_name, business_type = get_business_context(db, tenant_id)

    system_prompt = build_post_system_prompt(
        business_name=business_name,
        business_type=business_type,
        platform=req.platform,
        tone=req.tone,
        include_hashtags=req.include_hashtags,
    )

    try:
        resp = await call_claude_messages(
            operation="social.generate_post",
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0.7,
            timeout=30.0,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Create a {req.platform} post about: {req.topic}",
            }],
            metadata={
                "tenant_id": tenant_id,
                "platform": req.platform,
                "tone": req.tone,
                "include_hashtags": req.include_hashtags,
            },
        )
        raw = resp.text.strip()
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited -- please try again in a moment")
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during social media generation")
        raise HTTPException(status_code=502, detail="AI service configuration error")
    except anthropic.APIError as e:
        logger.error("Anthropic API error during social media generation: %s", str(e))
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")
    except Exception:
        logger.exception("Social media AI generation failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="AI content generation failed")

    return parse_post_response(raw, req.platform)


@router.post("/{tenant_id}/generate-campaign")
async def generate_campaign_content(
    tenant_id: str,
    req: AICampaignRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate a week of social media content across platforms."""
    verify_tenant(claims, tenant_id)

    for platform in req.platforms:
        _validate_platform(platform)

    db = get_service_supabase()
    business_name, business_type = get_business_context(db, tenant_id)

    system_prompt = build_campaign_system_prompt(
        business_name=business_name,
        business_type=business_type,
        platforms=req.platforms,
        posts_per_week=req.posts_per_week,
    )

    try:
        resp = await call_claude_messages(
            operation="social.generate_campaign",
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.7,
            timeout=60.0,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Topic: {req.topic}\nPlatforms: {', '.join(req.platforms)}\nPosts: {req.posts_per_week}",
            }],
            metadata={
                "tenant_id": tenant_id,
                "platform_count": len(req.platforms),
                "posts_per_week": req.posts_per_week,
            },
        )
        raw = resp.text.strip()
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited -- please try again in a moment")
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during campaign generation")
        raise HTTPException(status_code=502, detail="AI service configuration error")
    except anthropic.APIError as e:
        logger.error("Anthropic API error during campaign generation: %s", str(e))
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")
    except Exception:
        logger.exception("Campaign AI generation failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="AI campaign generation failed")

    posts = parse_generated_campaign_posts(raw, req.platforms)

    return {
        "posts": posts,
        "total_generated": len(posts),
        "topic": req.topic,
        "platforms": req.platforms,
    }


@router.post("/{tenant_id}/generate-image", response_model=SocialImageGenerateResponse)
async def generate_post_image_endpoint(
    tenant_id: str,
    req: SocialImageGenerateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI-generate a platform-sized image and upload it to storage.

    When ``post_id`` is set, appends the generated URL to that post's
    ``media_urls`` (best-effort — a failure to append does not fail the
    request; the image is already generated and returned to the caller).
    """
    verify_tenant(claims, tenant_id)
    _validate_platform(req.platform)

    db = get_service_supabase()

    try:
        result = await generate_post_image(
            db, tenant_id=tenant_id, prompt=req.prompt, platform=req.platform
        )
    except SocialImageGenError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Social media image generation failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Image generation failed")

    if req.post_id:
        try:
            existing = (
                db.table("social_posts")
                .select("media_urls")
                .eq("id", req.post_id)
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                media_urls = list(existing.data[0].get("media_urls") or [])
                media_urls.append(result["url"])
                db.table("social_posts").update(
                    {
                        "media_urls": media_urls,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", req.post_id).eq("tenant_id", tenant_id).execute()
            else:
                logger.warning(
                    "generate-image: post_id %s not found for tenant %s -- image generated but not attached",
                    req.post_id,
                    tenant_id,
                )
        except Exception:
            logger.exception(
                "Failed to append generated image to post %s for tenant %s",
                req.post_id,
                tenant_id,
            )
            # Image itself was generated + stored successfully -- don't fail
            # the whole request over the media_urls append.

    return SocialImageGenerateResponse(**result)


# --- Calendar View ---

@router.get("/{tenant_id}/calendar")
async def get_calendar(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
):
    """Get social media posts in a calendar view, grouped by date."""
    verify_tenant(claims, tenant_id)

    _, last_day = monthrange(year, month)
    start_date = f"{year}-{month:02d}-01T00:00:00Z"
    end_date = f"{year}-{month:02d}-{last_day}T23:59:59Z"

    try:
        db = get_service_supabase()

        scheduled = (
            db.table("social_posts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .gte("scheduled_for", start_date)
            .lte("scheduled_for", end_date)
            .order("scheduled_for")
            .execute()
        )

        published = (
            db.table("social_posts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .gte("published_at", start_date)
            .lte("published_at", end_date)
            .is_("scheduled_for", "null")
            .order("published_at")
            .execute()
        )

        drafts = (
            db.table("social_posts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("status", "draft")
            .gte("created_at", start_date)
            .lte("created_at", end_date)
            .is_("scheduled_for", "null")
            .order("created_at")
            .execute()
        )

        all_posts: dict = {}
        for post in (scheduled.data or []) + (published.data or []) + (drafts.data or []):
            all_posts[post["id"]] = post
        all_posts_list = list(all_posts.values())

        calendar: dict[str, list] = {}
        for post in all_posts_list:
            date_key = None
            if post.get("scheduled_for"):
                date_key = post["scheduled_for"][:10]
            elif post.get("published_at"):
                date_key = post["published_at"][:10]
            elif post.get("created_at"):
                date_key = post["created_at"][:10]

            if date_key:
                calendar.setdefault(date_key, []).append(post)

        return {
            "month": month,
            "year": year,
            "calendar": calendar,
            "total_posts": len(all_posts_list),
        }
    except Exception:
        logger.exception("Failed to get social calendar for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load calendar")


# --- Analytics ---

@router.get("/{tenant_id}/analytics")
async def get_analytics(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get social media analytics summary."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        all_posts = (
            db.table("social_posts")
            .select("id, platform, status, created_at")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        posts = all_posts.data or []

        by_platform: dict = {}
        by_status: dict = {}
        for post in posts:
            plat = post["platform"]
            stat = post["status"]
            by_platform[plat] = by_platform.get(plat, 0) + 1
            by_status[stat] = by_status.get(stat, 0) + 1

        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent = (
            db.table("social_posts")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", thirty_days_ago[:10] + "T00:00:00Z")
            .execute()
        )
        posts_last_30 = recent.count if recent.count is not None else 0

        return {
            "total_posts": len(posts),
            "by_platform": by_platform,
            "by_status": by_status,
            "posts_last_30_days": posts_last_30,
            "avg_posts_per_week": round(posts_last_30 / 4.3, 1) if posts_last_30 > 0 else 0,
        }
    except Exception:
        logger.exception("Failed to get social analytics for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load analytics")
