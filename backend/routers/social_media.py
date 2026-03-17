"""Social Media Marketing endpoints — post management, AI content generation, calendar, analytics."""

import logging
from datetime import datetime, timedelta, timezone
from calendar import monthrange

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/social", tags=["social-media"])

VALID_PLATFORMS = {"facebook", "instagram", "twitter", "linkedin", "google_business"}
VALID_STATUSES = {"draft", "scheduled", "published", "failed"}

# Platform-specific constraints for AI generation
PLATFORM_LIMITS = {
    "facebook": {
        "max_chars": 2000,
        "hashtag_style": "Minimal or no hashtags. 0-3 at most.",
        "tone": "Casual and conversational. Short paragraphs. Emojis sparingly.",
    },
    "instagram": {
        "max_chars": 2200,
        "hashtag_style": "Include 15-25 relevant hashtags on a separate line at the end.",
        "tone": "Visual, emotive, punchy. Use emojis naturally.",
    },
    "twitter": {
        "max_chars": 280,
        "hashtag_style": "1-3 hashtags woven into the text naturally.",
        "tone": "Concise, witty, direct. Every word counts.",
    },
    "linkedin": {
        "max_chars": 3000,
        "hashtag_style": "3-5 professional hashtags at the end.",
        "tone": "Professional, thought-leadership, value-driven. Use line breaks for readability.",
    },
    "google_business": {
        "max_chars": 1500,
        "hashtag_style": "No hashtags.",
        "tone": "Local SEO optimized. Mention location/service area. Clear call to action.",
    },
}


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


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _validate_platform(platform: str) -> None:
    if platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )


def _validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )


def _get_business_context(db, tenant_id: str) -> tuple[str, str]:
    """Fetch business name and type for AI context."""
    try:
        result = (
            db.table("tenants")
            .select("business_name, business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return (
                result.data[0].get("business_name", "the business"),
                result.data[0].get("business_type", ""),
            )
    except Exception:
        logger.warning("Failed to fetch business context for tenant %s", tenant_id, exc_info=True)
    return ("the business", "")


# --- Post CRUD Endpoints ---

@router.post("/{tenant_id}/posts")
async def create_post(
    tenant_id: str,
    req: SocialPostCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a social media post."""
    _verify_tenant(claims, tenant_id)
    _validate_platform(req.platform)

    status = "draft"
    if req.scheduled_for:
        status = "scheduled"

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
        db = get_supabase()
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
    _verify_tenant(claims, tenant_id)

    if platform:
        _validate_platform(platform)
    if status:
        _validate_status(status)

    try:
        db = get_supabase()
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

        # Total count
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
    _verify_tenant(claims, tenant_id)

    if req.platform:
        _validate_platform(req.platform)
    if req.status:
        _validate_status(req.status)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        db = get_supabase()
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
    _verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
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
    _verify_tenant(claims, tenant_id)
    _validate_platform(req.platform)

    db = get_supabase()
    business_name, business_type = _get_business_context(db, tenant_id)

    platform_info = PLATFORM_LIMITS[req.platform]
    biz_context = f" for {business_name}" + (f", a {business_type}" if business_type else "")

    tone_instruction = ""
    if req.tone:
        tone_instruction = f"\nTone: {req.tone}."
    else:
        tone_instruction = f"\nTone: {platform_info['tone']}"

    hashtag_instruction = ""
    if req.include_hashtags:
        hashtag_instruction = f"\nHashtags: {platform_info['hashtag_style']}"
    else:
        hashtag_instruction = "\nDo NOT include any hashtags."

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0.7,
            system=(
                f"You are a social media marketing expert creating content{biz_context}. "
                f"Generate a {req.platform} post about the given topic. "
                f"Keep it under {platform_info['max_chars']} characters."
                f"{tone_instruction}"
                f"{hashtag_instruction}\n\n"
                "Return ONLY the post content. If hashtags are included, put them on a separate "
                "line at the end prefixed with 'HASHTAGS:' on its own line, then the hashtags."
            ),
            messages=[{
                "role": "user",
                "content": f"Create a {req.platform} post about: {req.topic}",
            }],
        )
        raw = resp.content[0].text.strip()
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

    # Parse hashtags from response
    content = raw
    hashtags = []
    if "HASHTAGS:" in raw:
        parts = raw.split("HASHTAGS:", 1)
        content = parts[0].strip()
        hashtag_text = parts[1].strip()
        hashtags = [h.strip().lstrip("#") for h in hashtag_text.replace(",", " ").split() if h.strip()]
        hashtags = [f"#{h}" for h in hashtags if h]

    return {
        "content": content,
        "hashtags": hashtags,
        "character_count": len(content),
        "platform": req.platform,
    }


@router.post("/{tenant_id}/generate-campaign")
async def generate_campaign_content(
    tenant_id: str,
    req: AICampaignRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate a week of social media content across platforms."""
    _verify_tenant(claims, tenant_id)

    for platform in req.platforms:
        _validate_platform(platform)

    db = get_supabase()
    business_name, business_type = _get_business_context(db, tenant_id)
    biz_context = f" for {business_name}" + (f", a {business_type}" if business_type else "")

    platforms_desc = "\n".join(
        f"- {p}: max {PLATFORM_LIMITS[p]['max_chars']} chars, {PLATFORM_LIMITS[p]['tone']} {PLATFORM_LIMITS[p]['hashtag_style']}"
        for p in req.platforms
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.7,
            system=(
                f"You are a social media content strategist{biz_context}. "
                f"Create a week-long content calendar with {req.posts_per_week} posts about the given topic. "
                "Distribute posts across the specified platforms.\n\n"
                f"Platforms and guidelines:\n{platforms_desc}\n\n"
                "For each post, output in this exact format:\n"
                "===POST===\n"
                "DAY: [1-7]\n"
                "PLATFORM: [platform_name]\n"
                "CONTENT: [the post content]\n"
                "HASHTAGS: [comma-separated hashtags or 'none']\n\n"
                "Generate exactly the requested number of posts. Vary the days and platforms. "
                "Each post should have a unique angle on the topic."
            ),
            messages=[{
                "role": "user",
                "content": f"Topic: {req.topic}\nPlatforms: {', '.join(req.platforms)}\nPosts: {req.posts_per_week}",
            }],
        )
        raw = resp.content[0].text.strip()
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

    # Parse the response into individual posts
    posts = []
    sections = raw.split("===POST===")
    for section in sections:
        section = section.strip()
        if not section:
            continue

        post = {"day": 1, "platform": req.platforms[0], "content": "", "hashtags": []}
        lines = section.split("\n")
        content_lines = []
        in_content = False

        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("DAY:"):
                try:
                    post["day"] = int(stripped.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
                in_content = False
            elif stripped.upper().startswith("PLATFORM:"):
                plat = stripped.split(":", 1)[1].strip().lower().replace(" ", "_")
                if plat in VALID_PLATFORMS:
                    post["platform"] = plat
                in_content = False
            elif stripped.upper().startswith("CONTENT:"):
                content_start = stripped.split(":", 1)[1].strip()
                if content_start:
                    content_lines.append(content_start)
                in_content = True
            elif stripped.upper().startswith("HASHTAGS:"):
                hashtag_text = stripped.split(":", 1)[1].strip()
                if hashtag_text.lower() != "none":
                    post["hashtags"] = [
                        h.strip() if h.strip().startswith("#") else f"#{h.strip()}"
                        for h in hashtag_text.split(",")
                        if h.strip()
                    ]
                in_content = False
            elif in_content:
                content_lines.append(line)

        post["content"] = "\n".join(content_lines).strip()
        if post["content"]:
            posts.append(post)

    return {
        "posts": posts,
        "total_generated": len(posts),
        "topic": req.topic,
        "platforms": req.platforms,
    }


# --- Calendar View ---

@router.get("/{tenant_id}/calendar")
async def get_calendar(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
):
    """Get social media posts in a calendar view, grouped by date."""
    _verify_tenant(claims, tenant_id)

    _, last_day = monthrange(year, month)
    start_date = f"{year}-{month:02d}-01T00:00:00Z"
    end_date = f"{year}-{month:02d}-{last_day}T23:59:59Z"

    try:
        db = get_supabase()

        # Get scheduled/published posts in the date range
        scheduled = (
            db.table("social_posts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .gte("scheduled_for", start_date)
            .lte("scheduled_for", end_date)
            .order("scheduled_for")
            .execute()
        )

        # Also get posts published in this range
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

        # Also get draft posts created in this range (for planning view)
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

        # Merge and deduplicate
        all_posts = {}
        for post in (scheduled.data or []) + (published.data or []) + (drafts.data or []):
            all_posts[post["id"]] = post
        all_posts_list = list(all_posts.values())

        # Group by date
        calendar = {}
        for post in all_posts_list:
            date_key = None
            if post.get("scheduled_for"):
                date_key = post["scheduled_for"][:10]
            elif post.get("published_at"):
                date_key = post["published_at"][:10]
            elif post.get("created_at"):
                date_key = post["created_at"][:10]

            if date_key:
                if date_key not in calendar:
                    calendar[date_key] = []
                calendar[date_key].append(post)

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
    _verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()

        # Total posts by platform
        all_posts = (
            db.table("social_posts")
            .select("id, platform, status, created_at")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        posts = all_posts.data or []

        by_platform = {}
        by_status = {}
        for post in posts:
            plat = post["platform"]
            stat = post["status"]
            by_platform[plat] = by_platform.get(plat, 0) + 1
            by_status[stat] = by_status.get(stat, 0) + 1

        # Posting frequency (posts in last 30 days)
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
