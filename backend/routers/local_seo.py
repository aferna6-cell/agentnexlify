"""Local SEO Tools endpoints — profile completeness analysis and keyword suggestions."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/seo", tags=["local-seo"])


# ---------------------------------------------------------------------------
# Pydantic models — field names match seo_profiles table columns
# ---------------------------------------------------------------------------


class SEOProfileResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    completeness_score: int = 0
    missing_fields: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    keyword_suggestions: List[str] = Field(default_factory=list)
    last_analyzed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DashboardWidgetResponse(BaseModel):
    completeness_score: int = 0
    top_recommendations: List[str] = Field(default_factory=list)
    review_count: int = 0
    keyword_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _calculate_completeness(
    tenant: dict,
    widget_config: Optional[dict],
    faq_count: int,
    review_count: int,
    content_count: int,
) -> tuple[int, list[str], list[str]]:
    """Calculate completeness score (0-100), missing fields, and recommendations."""
    score = 0
    missing: list[str] = []
    recommendations: list[str] = []

    # Has business name (10pts)
    if tenant.get("business_name"):
        score += 10
    else:
        missing.append("business_name")
        recommendations.append("Add your business name to your profile.")

    # Has city (10pts)
    if tenant.get("city"):
        score += 10
    else:
        missing.append("city")
        recommendations.append("Add your city to help with local search visibility.")

    # Has website URL (10pts)
    if tenant.get("website_url"):
        score += 10
    else:
        missing.append("website_url")
        recommendations.append("Add your website URL to improve your online presence.")

    # Has business type (10pts)
    if tenant.get("business_type"):
        score += 10
    else:
        missing.append("business_type")
        recommendations.append("Set your business type to get better keyword suggestions.")

    # Has FAQs (15pts, scaled by count up to 10)
    if faq_count > 0:
        faq_score = min(faq_count, 10) / 10 * 15
        score += int(faq_score)
    else:
        missing.append("faq_entries")
        recommendations.append("Add FAQ entries to help your AI assistant and boost SEO content.")

    # Has reviews (15pts)
    if review_count > 0:
        score += 15
    else:
        missing.append("reviews")
        recommendations.append("Collect customer reviews to build trust and improve local rankings.")

    # Has widget configured with custom greeting (10pts)
    if widget_config and widget_config.get("greeting_message"):
        score += 10
    else:
        missing.append("widget_greeting")
        recommendations.append("Set a custom widget greeting message for better visitor engagement.")

    # Has content items (10pts)
    if content_count > 0:
        score += 10
    else:
        missing.append("content_items")
        recommendations.append("Create content to establish authority in your local market.")

    # Has booking enabled (10pts)
    if widget_config and widget_config.get("booking_enabled"):
        score += 10
    else:
        missing.append("booking_enabled")
        recommendations.append("Enable appointment booking to convert more website visitors.")

    return score, missing, recommendations


async def _generate_keywords(business_type: Optional[str], city: Optional[str]) -> list[str]:
    """Use Claude to generate local keyword suggestions based on business type and city."""
    if not business_type and not city:
        return []

    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping keyword generation")
        return []

    location_desc = city or "your area"
    biz_desc = business_type or "local business"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            temperature=0.5,
            system=(
                "You are a local SEO expert. Return ONLY a JSON array of keyword strings. "
                "No explanations, no markdown, just the raw JSON array."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Generate 10-15 high-value local SEO keywords for a {biz_desc} "
                    f"in {location_desc}. Include a mix of:\n"
                    "- Service-based keywords (e.g., 'emergency plumber near me')\n"
                    "- Location-based keywords (e.g., 'plumber in [city]')\n"
                    "- Long-tail keywords (e.g., 'best affordable plumber [city]')\n"
                    "Return ONLY the JSON array."
                ),
            }],
        )
        raw = resp.content[0].text.strip()
        keywords = json.loads(raw)
        if isinstance(keywords, list):
            return [str(k) for k in keywords[:20]]
        logger.warning("Claude returned non-list for keywords: %s", type(keywords))
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse keyword suggestions JSON from Claude: %.200s", raw)
        return []
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during keyword generation")
        return []
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during keyword generation")
        return []
    except anthropic.APIError as e:
        logger.error("Anthropic API error during keyword generation: %s", str(e))
        return []
    except Exception:
        logger.error("Keyword generation failed unexpectedly", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/analyze", response_model=SEOProfileResponse)
async def analyze_seo_profile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Analyze the tenant's profile for SEO completeness and generate keyword suggestions."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load tenant data
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city, website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to load tenant %s for SEO analysis", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load tenant data")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]

    # Load widget config
    widget_config = None
    try:
        wc_result = (
            db.table("widget_configs")
            .select("greeting_message, booking_enabled")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if wc_result.data:
            widget_config = wc_result.data[0]
    except Exception:
        logger.warning("Failed to load widget config for tenant %s", tenant_id, exc_info=True)

    # Load FAQ count
    faq_count = 0
    try:
        faq_result = (
            db.table("faq_entries")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        faq_count = faq_result.count or 0
    except Exception:
        logger.warning("Failed to count FAQs for tenant %s", tenant_id, exc_info=True)

    # Load review count
    review_count = 0
    try:
        review_result = (
            db.table("reviews")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        review_count = review_result.count or 0
    except Exception:
        logger.warning("Failed to count reviews for tenant %s", tenant_id, exc_info=True)

    # Load content count
    content_count = 0
    try:
        content_result = (
            db.table("content_items")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        content_count = content_result.count or 0
    except Exception:
        logger.warning("Failed to count content items for tenant %s", tenant_id, exc_info=True)

    # Calculate completeness
    score, missing, recommendations = _calculate_completeness(
        tenant, widget_config, faq_count, review_count, content_count,
    )

    # Generate keyword suggestions via Claude
    keywords = await _generate_keywords(
        tenant.get("business_type"), tenant.get("city"),
    )

    now = datetime.now(timezone.utc).isoformat()

    # Upsert to seo_profiles: check if exists, then insert or update
    profile_data = {
        "tenant_id": tenant_id,
        "completeness_score": score,
        "missing_fields": missing,
        "recommendations": recommendations,
        "keyword_suggestions": keywords,
        "last_analyzed_at": now,
        "updated_at": now,
    }

    try:
        existing = (
            db.table("seo_profiles")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            result = (
                db.table("seo_profiles")
                .update(profile_data)
                .eq("tenant_id", tenant_id)
                .execute()
            )
        else:
            result = (
                db.table("seo_profiles")
                .insert(profile_data)
                .execute()
            )

        saved = result.data[0] if result.data else profile_data
    except Exception:
        logger.error("Failed to save SEO profile for tenant %s", tenant_id, exc_info=True)
        # Return computed data even if DB save failed
        saved = profile_data

    return SEOProfileResponse(
        id=saved.get("id"),
        tenant_id=tenant_id,
        completeness_score=score,
        missing_fields=missing,
        recommendations=recommendations,
        keyword_suggestions=keywords,
        last_analyzed_at=now,
        created_at=saved.get("created_at"),
        updated_at=saved.get("updated_at", now),
    )


@router.get("/{tenant_id}", response_model=SEOProfileResponse)
async def get_seo_profile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the cached SEO profile for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        result = (
            db.table("seo_profiles")
            .select("*")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch SEO profile for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch SEO profile")

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No SEO profile found. Run an analysis first.",
        )

    profile = result.data[0]
    return SEOProfileResponse(
        id=profile.get("id"),
        tenant_id=profile.get("tenant_id", tenant_id),
        completeness_score=profile.get("completeness_score", 0),
        missing_fields=profile.get("missing_fields", []),
        recommendations=profile.get("recommendations", []),
        keyword_suggestions=profile.get("keyword_suggestions", []),
        last_analyzed_at=profile.get("last_analyzed_at"),
        created_at=profile.get("created_at"),
        updated_at=profile.get("updated_at"),
    )


@router.get("/{tenant_id}/keywords")
async def get_keyword_suggestions(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get keyword suggestions from the cached SEO profile."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        result = (
            db.table("seo_profiles")
            .select("keyword_suggestions")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch keywords for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch keyword suggestions")

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No SEO profile found. Run an analysis first.",
        )

    keywords = result.data[0].get("keyword_suggestions", [])
    return {"tenant_id": tenant_id, "keywords": keywords}


@router.get("/{tenant_id}/dashboard-widget", response_model=DashboardWidgetResponse)
async def get_dashboard_widget(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return a summary card for the main dashboard."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load SEO profile
    completeness_score = 0
    recommendations: list[str] = []
    keyword_count = 0

    try:
        profile_result = (
            db.table("seo_profiles")
            .select("completeness_score, recommendations, keyword_suggestions")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if profile_result.data:
            profile = profile_result.data[0]
            completeness_score = profile.get("completeness_score", 0)
            all_recs = profile.get("recommendations", [])
            recommendations = all_recs[:3] if isinstance(all_recs, list) else []
            kw = profile.get("keyword_suggestions", [])
            keyword_count = len(kw) if isinstance(kw, list) else 0
    except Exception:
        logger.warning("Failed to load SEO profile for dashboard widget, tenant %s", tenant_id, exc_info=True)

    # Load review count
    review_count = 0
    try:
        review_result = (
            db.table("reviews")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        review_count = review_result.count or 0
    except Exception:
        logger.warning("Failed to count reviews for dashboard widget, tenant %s", tenant_id, exc_info=True)

    return DashboardWidgetResponse(
        completeness_score=completeness_score,
        top_recommendations=recommendations,
        review_count=review_count,
        keyword_count=keyword_count,
    )
