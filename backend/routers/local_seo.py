"""Local SEO Tools endpoints — profile completeness, SEO audit, GEO scoring, keyword tracking."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/seo", tags=["local-seo"])


# ---------------------------------------------------------------------------
# Pydantic models — field names match database table columns
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


# --- SEO Audit models (match seo_audits table) ---

class SEOIssue(BaseModel):
    category: str
    severity: str  # "critical", "warning", "passed"
    title: str
    description: str
    recommendation: Optional[str] = None
    page_url: Optional[str] = None


class SEOCategoryScore(BaseModel):
    score: int = 0
    issues: List[SEOIssue] = Field(default_factory=list)


class SEOAuditResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    overall_score: int = 0
    categories: Dict[str, Any] = Field(default_factory=dict)
    critical_issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    passed_checks: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    pages_analyzed: int = 0
    created_at: Optional[str] = None


class SEOAuditHistoryItem(BaseModel):
    id: str
    overall_score: int = 0
    pages_analyzed: int = 0
    critical_count: int = 0
    warning_count: int = 0
    passed_count: int = 0
    created_at: Optional[str] = None


# --- GEO Score models (match geo_scores table) ---

class GEOScoreRequest(BaseModel):
    business_name: Optional[str] = Field(None, max_length=200)
    business_type: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=2000)


class GEOScoreResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    overall_score: int = 0
    platform_scores: Dict[str, Any] = Field(default_factory=dict)
    visibility_factors: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None


# --- Keyword Tracking models (match keyword_rankings table) ---

class KeywordTrackRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1, max_length=20)


class KeywordRankingItem(BaseModel):
    id: Optional[str] = None
    keyword: str
    difficulty_score: int = 50
    estimated_position: Optional[str] = None
    search_volume_estimate: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    last_analyzed_at: Optional[str] = None


class KeywordRankingsResponse(BaseModel):
    tenant_id: str
    keywords: List[KeywordRankingItem] = Field(default_factory=list)


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
    raw = ""

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


async def _run_seo_audit_ai(pages_json: list, extracted_text: str, business_name: str, business_type: str) -> dict:
    """Use Claude AI to perform comprehensive SEO analysis on crawled website content."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping SEO audit AI analysis")
        return {}

    # Build a summary of pages for analysis
    page_summaries = []
    for page in pages_json[:20]:  # Limit to 20 pages to manage token usage
        page_url = page.get("url", "unknown")
        page_content = page.get("content", page.get("markdown", page.get("text", "")))
        # Truncate each page to keep total prompt reasonable
        if isinstance(page_content, str) and len(page_content) > 3000:
            page_content = page_content[:3000] + "\n[truncated]"
        page_summaries.append(f"--- PAGE: {page_url} ---\n{page_content}")

    all_pages_text = "\n\n".join(page_summaries)
    # Cap total content at ~30KB to stay within token limits
    if len(all_pages_text) > 30000:
        all_pages_text = all_pages_text[:30000] + "\n\n[Additional pages truncated]"

    prompt = f"""Analyze this website for SEO quality. The business is "{business_name}" ({business_type}).

WEBSITE CONTENT:
{all_pages_text}

Analyze these SEO factors and return a JSON object with this EXACT structure:
{{
  "overall_score": <0-100 integer>,
  "categories": {{
    "technical": {{
      "score": <0-100>,
      "issues": [
        {{"severity": "critical|warning|passed", "title": "...", "description": "...", "recommendation": "..."}}
      ]
    }},
    "content": {{
      "score": <0-100>,
      "issues": [...]
    }},
    "on_page": {{
      "score": <0-100>,
      "issues": [...]
    }},
    "user_experience": {{
      "score": <0-100>,
      "issues": [...]
    }}
  }},
  "recommendations": ["actionable recommendation 1", "actionable recommendation 2", ...]
}}

Check for:
TECHNICAL:
- Meta titles present, unique, 50-60 chars
- Meta descriptions present, unique, 150-160 chars
- Heading structure (single H1 per page, logical H2-H6 hierarchy)
- Image alt text coverage
- Internal linking structure
- HTTPS usage
- Canonical tags
- robots.txt/sitemap indicators

CONTENT:
- Content quality and depth
- Keyword usage and density
- Duplicate content indicators
- Fresh/dated content
- Content length per page
- Local SEO content (city/location mentions)

ON-PAGE:
- URL structure (clean, descriptive)
- Schema markup indicators
- Open Graph / social meta tags
- Mobile viewport meta
- External link quality

USER EXPERIENCE:
- Page structure clarity
- Navigation depth
- Call-to-action presence
- Contact information visibility
- Mobile-friendly indicators from HTML structure

Return ONLY the raw JSON object, no markdown fences or explanations."""
    raw = ""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.2,
            system=(
                "You are an expert SEO auditor. Analyze websites and return structured JSON audit results. "
                "Be specific and actionable in your recommendations. Score fairly based on actual evidence in the content. "
                "Return ONLY valid JSON, no markdown fences."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        logger.warning("SEO audit AI returned non-dict: %s", type(result))
        return {}
    except json.JSONDecodeError:
        logger.error("Failed to parse SEO audit JSON from Claude: %.500s", raw)
        return {}
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during SEO audit")
        return {}
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during SEO audit")
        return {}
    except anthropic.APIError as e:
        logger.error("Anthropic API error during SEO audit: %s", str(e))
        return {}
    except Exception:
        logger.error("SEO audit AI analysis failed unexpectedly", exc_info=True)
        return {}


async def _run_geo_score_ai(
    business_name: str,
    business_type: str,
    city: str,
    website_url: str,
    extracted_text: Optional[str] = None,
) -> dict:
    """Use Claude AI to estimate GEO (Generative Engine Optimization) visibility."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping GEO scoring")
        return {}

    website_context = ""
    if extracted_text:
        truncated = extracted_text[:5000]
        if len(extracted_text) > 5000:
            truncated += "\n[truncated]"
        website_context = f"\n\nWEBSITE CONTENT SAMPLE:\n{truncated}"

    prompt = f"""Evaluate the AI/GEO (Generative Engine Optimization) visibility for this business:

Business Name: {business_name}
Business Type: {business_type}
City: {city}
Website: {website_url}{website_context}

GEO (Generative Engine Optimization) measures how visible and recommendable a business is when people ask AI assistants (ChatGPT, Claude, Perplexity, Google Gemini) for local business recommendations.

Analyze and return a JSON object with this EXACT structure:
{{
  "overall_score": <0-100 integer>,
  "platform_scores": {{
    "chatgpt": <0-100>,
    "claude": <0-100>,
    "perplexity": <0-100>,
    "gemini": <0-100>
  }},
  "visibility_factors": [
    {{
      "factor": "factor name",
      "status": "strong|moderate|weak",
      "score": <0-100>,
      "explanation": "why this matters and current state"
    }}
  ],
  "recommendations": [
    "specific actionable recommendation 1",
    "specific actionable recommendation 2"
  ]
}}

Evaluate these visibility factors:
1. Brand Authority — Is this business likely known to AI training data? (reviews, press, citations)
2. Content Quality — Does the website have substantive, unique content AI can learn from?
3. Local Citations — Would the business appear in local directories, Google Business, Yelp, etc.?
4. Structured Data — Does the website have schema markup that AI can parse?
5. Topical Authority — Is the website focused and authoritative in its niche?
6. Review Presence — Are there reviews AI platforms might index?
7. Social Signals — Social media presence and engagement
8. E-E-A-T Signals — Experience, Expertise, Authoritativeness, Trustworthiness

Score conservatively. Most small local businesses score 20-50 unless they have strong online presence.
Return ONLY the raw JSON object, no markdown fences."""
    raw = ""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=45.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.3,
            system=(
                "You are an expert in GEO (Generative Engine Optimization) and AI visibility. "
                "Score businesses on how likely AI platforms are to recommend them. "
                "Be realistic and conservative — most small businesses have low AI visibility. "
                "Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        logger.warning("GEO score AI returned non-dict: %s", type(result))
        return {}
    except json.JSONDecodeError:
        logger.error("Failed to parse GEO score JSON from Claude: %.500s", raw)
        return {}
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during GEO scoring")
        return {}
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during GEO scoring")
        return {}
    except anthropic.APIError as e:
        logger.error("Anthropic API error during GEO scoring: %s", str(e))
        return {}
    except Exception:
        logger.error("GEO scoring AI analysis failed unexpectedly", exc_info=True)
        return {}


async def _analyze_keywords_ai(
    keywords: list[str],
    business_type: str,
    city: str,
) -> list[dict]:
    """Use Claude AI to analyze keyword competitiveness and ranking potential."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping keyword analysis")
        return []

    keywords_str = "\n".join(f"- {kw}" for kw in keywords)
    prompt = f"""Analyze these keywords for a {business_type} in {city}:

{keywords_str}

For each keyword, return a JSON array of objects with this EXACT structure:
[
  {{
    "keyword": "the keyword",
    "difficulty_score": <1-100 integer, 100 being hardest>,
    "estimated_position": "1-3" or "4-10" or "11-20" or "21-50" or "50+",
    "search_volume_estimate": "high" or "medium" or "low" or "very_low",
    "recommendations": ["recommendation 1", "recommendation 2"]
  }}
]

Guidelines:
- difficulty_score: Consider competition level. Generic keywords (e.g., "plumber") are 80-100. Long-tail local keywords (e.g., "emergency plumber in [small city]") are 20-50.
- estimated_position: Where a well-optimized local business page would likely rank. Be realistic.
- search_volume_estimate: Relative search volume for the local market.
- recommendations: 1-3 specific tips to rank for this keyword.

Return ONLY the raw JSON array, no markdown fences."""
    raw = ""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=45.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            system=(
                "You are an expert local SEO analyst. Analyze keyword competitiveness for local businesses. "
                "Be realistic about ranking potential. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        logger.warning("Keyword analysis AI returned non-list: %s", type(result))
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse keyword analysis JSON from Claude: %.500s", raw)
        return []
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during keyword analysis")
        return []
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during keyword analysis")
        return []
    except anthropic.APIError as e:
        logger.error("Anthropic API error during keyword analysis: %s", str(e))
        return []
    except Exception:
        logger.error("Keyword analysis AI failed unexpectedly", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Existing Endpoints (unchanged)
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


# ---------------------------------------------------------------------------
# SEO Audit Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/audit", response_model=SEOAuditResponse)
async def run_seo_audit(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Run a full SEO audit using crawled website content and Claude AI analysis."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load tenant info
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city, website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to load tenant %s for SEO audit", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load tenant data")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]

    # Load crawled website content
    try:
        crawl_result = (
            db.table("website_content")
            .select("pages_json, extracted_text, crawl_status, pages_found")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to load website content for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load website content")

    if not crawl_result.data:
        raise HTTPException(
            status_code=400,
            detail="No crawled website content found. Please scan your website first using the Website Scanner in Settings.",
        )

    crawl = crawl_result.data[0]
    if crawl.get("crawl_status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Website crawl status is '{crawl.get('crawl_status', 'unknown')}'. Please complete a website scan first.",
        )

    pages_json = crawl.get("pages_json") or []
    extracted_text = crawl.get("extracted_text") or ""
    pages_found = crawl.get("pages_found", 0)

    if not pages_json and not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Crawled content is empty. Please re-scan your website.",
        )

    # Run AI analysis
    business_name = tenant.get("business_name") or "Unknown Business"
    business_type = tenant.get("business_type") or "local business"

    audit_result = await _run_seo_audit_ai(
        pages_json, extracted_text, business_name, business_type,
    )

    if not audit_result:
        raise HTTPException(
            status_code=500,
            detail="SEO audit analysis could not be completed. Please try again.",
        )

    # Extract structured data from AI result
    try:
        overall_score = int(audit_result.get("overall_score") or 0)
    except (TypeError, ValueError):
        logger.warning("AI returned non-integer overall_score: %s", audit_result.get("overall_score"))
        overall_score = 0
    categories = audit_result.get("categories", {})
    recommendations_list = audit_result.get("recommendations", [])

    # Categorize issues by severity
    critical_issues = []
    warnings = []
    passed_checks = []

    for cat_name, cat_data in categories.items():
        if not isinstance(cat_data, dict):
            continue
        for issue in cat_data.get("issues", []):
            if not isinstance(issue, dict):
                continue
            issue["category"] = cat_name
            severity = issue.get("severity", "warning")
            if severity == "critical":
                critical_issues.append(issue)
            elif severity == "warning":
                warnings.append(issue)
            elif severity == "passed":
                passed_checks.append(issue)

    # Save to seo_audits table
    audit_data = {
        "tenant_id": tenant_id,
        "overall_score": overall_score,
        "categories": categories,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "passed_checks": passed_checks,
        "recommendations": recommendations_list,
        "pages_analyzed": pages_found if isinstance(pages_found, int) else len(pages_json),
    }

    saved = audit_data
    try:
        insert_result = (
            db.table("seo_audits")
            .insert(audit_data)
            .execute()
        )
        if insert_result.data:
            saved = insert_result.data[0]
    except Exception:
        logger.error("Failed to save SEO audit for tenant %s", tenant_id, exc_info=True)
        # Still return computed results even if save fails

    return SEOAuditResponse(
        id=saved.get("id"),
        tenant_id=tenant_id,
        overall_score=overall_score,
        categories=categories,
        critical_issues=critical_issues,
        warnings=warnings,
        passed_checks=passed_checks,
        recommendations=recommendations_list,
        pages_analyzed=audit_data["pages_analyzed"],
        created_at=saved.get("created_at"),
    )


@router.get("/{tenant_id}/audit", response_model=SEOAuditResponse)
async def get_latest_audit(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the latest SEO audit results for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        result = (
            db.table("seo_audits")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch SEO audit for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch SEO audit")

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No SEO audit found. Run an audit first.",
        )

    audit = result.data[0]
    return SEOAuditResponse(
        id=audit.get("id"),
        tenant_id=audit.get("tenant_id", tenant_id),
        overall_score=audit.get("overall_score", 0),
        categories=audit.get("categories", {}),
        critical_issues=audit.get("critical_issues", []),
        warnings=audit.get("warnings", []),
        passed_checks=audit.get("passed_checks", []),
        recommendations=audit.get("recommendations", []),
        pages_analyzed=audit.get("pages_analyzed", 0),
        created_at=audit.get("created_at"),
    )


@router.get("/{tenant_id}/audit/history")
async def get_audit_history(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=90),
    claims: dict = Depends(_get_current_tenant),
):
    """Get SEO audit history for the last N days (default 30)."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = (
            db.table("seo_audits")
            .select("id, overall_score, pages_analyzed, critical_issues, warnings, passed_checks, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch audit history for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch audit history")

    history = []
    for audit in (result.data or []):
        critical_list = audit.get("critical_issues", [])
        warning_list = audit.get("warnings", [])
        passed_list = audit.get("passed_checks", [])
        history.append(SEOAuditHistoryItem(
            id=audit["id"],
            overall_score=audit.get("overall_score", 0),
            pages_analyzed=audit.get("pages_analyzed", 0),
            critical_count=len(critical_list) if isinstance(critical_list, list) else 0,
            warning_count=len(warning_list) if isinstance(warning_list, list) else 0,
            passed_count=len(passed_list) if isinstance(passed_list, list) else 0,
            created_at=audit.get("created_at"),
        ))

    return {"tenant_id": tenant_id, "audits": [h.model_dump() for h in history], "days": days}


# ---------------------------------------------------------------------------
# GEO (Generative Engine Optimization) Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/geo-score", response_model=GEOScoreResponse)
async def calculate_geo_score(
    tenant_id: str,
    body: GEOScoreRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Calculate GEO (Generative Engine Optimization) visibility score using Claude AI."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load tenant info for defaults
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city, website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to load tenant %s for GEO scoring", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load tenant data")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]

    # Use request body values or fall back to tenant data
    business_name = body.business_name or tenant.get("business_name") or "Unknown Business"
    business_type = body.business_type or tenant.get("business_type") or "local business"
    city = body.city or tenant.get("city") or "unknown"
    website_url = body.website_url or tenant.get("website_url") or ""

    if not business_name or business_name == "Unknown Business":
        raise HTTPException(
            status_code=400,
            detail="Business name is required. Set it in your profile or provide it in the request.",
        )

    # Optionally load crawled website content for better analysis
    extracted_text = None
    try:
        crawl_result = (
            db.table("website_content")
            .select("extracted_text")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if crawl_result.data:
            extracted_text = crawl_result.data[0].get("extracted_text")
    except Exception:
        logger.warning("Failed to load website content for GEO scoring, tenant %s", tenant_id, exc_info=True)

    # Run AI GEO analysis
    geo_result = await _run_geo_score_ai(
        business_name, business_type, city, website_url, extracted_text,
    )

    if not geo_result:
        raise HTTPException(
            status_code=500,
            detail="GEO analysis could not be completed. Please try again.",
        )

    try:
        overall_score = int(geo_result.get("overall_score") or 0)
    except (TypeError, ValueError):
        logger.warning("AI returned non-integer GEO overall_score: %s", geo_result.get("overall_score"))
        overall_score = 0
    platform_scores = geo_result.get("platform_scores", {})
    visibility_factors = geo_result.get("visibility_factors", [])
    recommendations_list = geo_result.get("recommendations", [])

    # Save to geo_scores table
    geo_data = {
        "tenant_id": tenant_id,
        "overall_score": overall_score,
        "platform_scores": platform_scores,
        "visibility_factors": visibility_factors,
        "recommendations": recommendations_list,
        "business_name": business_name,
        "business_type": business_type,
        "city": city,
        "website_url": website_url,
    }

    saved = geo_data
    try:
        insert_result = (
            db.table("geo_scores")
            .insert(geo_data)
            .execute()
        )
        if insert_result.data:
            saved = insert_result.data[0]
    except Exception:
        logger.error("Failed to save GEO score for tenant %s", tenant_id, exc_info=True)

    return GEOScoreResponse(
        id=saved.get("id"),
        tenant_id=tenant_id,
        overall_score=overall_score,
        platform_scores=platform_scores,
        visibility_factors=visibility_factors,
        recommendations=recommendations_list,
        created_at=saved.get("created_at"),
    )


@router.get("/{tenant_id}/geo-score", response_model=GEOScoreResponse)
async def get_latest_geo_score(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the latest GEO visibility score for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        result = (
            db.table("geo_scores")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch GEO score for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch GEO score")

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No GEO score found. Run a GEO analysis first.",
        )

    geo = result.data[0]
    return GEOScoreResponse(
        id=geo.get("id"),
        tenant_id=geo.get("tenant_id", tenant_id),
        overall_score=geo.get("overall_score", 0),
        platform_scores=geo.get("platform_scores", {}),
        visibility_factors=geo.get("visibility_factors", []),
        recommendations=geo.get("recommendations", []),
        created_at=geo.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Keyword Tracking Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/keywords/track", response_model=KeywordRankingsResponse)
async def track_keywords(
    tenant_id: str,
    body: KeywordTrackRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Add keywords to track and analyze their competitiveness using Claude AI."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load tenant info for context
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_type, city")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Failed to load tenant %s for keyword tracking", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load tenant data")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]
    business_type = tenant.get("business_type") or "local business"
    city = tenant.get("city") or "unknown"

    # Deduplicate and clean keywords
    cleaned_keywords = list(set(kw.strip().lower() for kw in body.keywords if kw.strip()))
    if not cleaned_keywords:
        raise HTTPException(status_code=400, detail="No valid keywords provided")

    # Run AI analysis
    analysis_results = await _analyze_keywords_ai(cleaned_keywords, business_type, city)

    # Build a lookup from the AI results
    ai_lookup: dict[str, dict] = {}
    for item in analysis_results:
        if isinstance(item, dict) and "keyword" in item:
            ai_lookup[item["keyword"].lower()] = item

    now = datetime.now(timezone.utc).isoformat()
    saved_items: list[KeywordRankingItem] = []

    for kw in cleaned_keywords:
        ai_data = ai_lookup.get(kw, {})

        ranking_data = {
            "tenant_id": tenant_id,
            "keyword": kw,
            "difficulty_score": int(ai_data.get("difficulty_score", 50)),
            "estimated_position": ai_data.get("estimated_position", "unknown"),
            "search_volume_estimate": ai_data.get("search_volume_estimate", "unknown"),
            "recommendations": ai_data.get("recommendations", []),
            "last_analyzed_at": now,
        }

        # Upsert: check if keyword already tracked, update or insert
        try:
            existing = (
                db.table("keyword_rankings")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("keyword", kw)
                .limit(1)
                .execute()
            )
            if existing.data:
                # Update existing record (omit tenant_id and keyword from update)
                update_data = {
                    "difficulty_score": ranking_data["difficulty_score"],
                    "estimated_position": ranking_data["estimated_position"],
                    "search_volume_estimate": ranking_data["search_volume_estimate"],
                    "recommendations": ranking_data["recommendations"],
                    "last_analyzed_at": now,
                }
                result = (
                    db.table("keyword_rankings")
                    .update(update_data)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
                saved = result.data[0] if result.data else ranking_data
            else:
                result = (
                    db.table("keyword_rankings")
                    .insert(ranking_data)
                    .execute()
                )
                saved = result.data[0] if result.data else ranking_data

            saved_items.append(KeywordRankingItem(
                id=saved.get("id"),
                keyword=kw,
                difficulty_score=saved.get("difficulty_score", 50),
                estimated_position=saved.get("estimated_position"),
                search_volume_estimate=saved.get("search_volume_estimate"),
                recommendations=saved.get("recommendations", []),
                last_analyzed_at=saved.get("last_analyzed_at"),
            ))
        except Exception:
            logger.error("Failed to save keyword ranking for '%s', tenant %s", kw, tenant_id, exc_info=True)
            # Still include the keyword with AI data even if DB save fails
            saved_items.append(KeywordRankingItem(
                keyword=kw,
                difficulty_score=ranking_data["difficulty_score"],
                estimated_position=ranking_data["estimated_position"],
                search_volume_estimate=ranking_data["search_volume_estimate"],
                recommendations=ranking_data["recommendations"],
                last_analyzed_at=now,
            ))

    return KeywordRankingsResponse(
        tenant_id=tenant_id,
        keywords=saved_items,
    )


@router.get("/{tenant_id}/keywords/rankings", response_model=KeywordRankingsResponse)
async def get_keyword_rankings(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get all tracked keyword rankings for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    try:
        result = (
            db.table("keyword_rankings")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("difficulty_score", desc=False)
            .execute()
        )
    except Exception:
        logger.error("Failed to fetch keyword rankings for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch keyword rankings")

    keywords = []
    for row in (result.data or []):
        keywords.append(KeywordRankingItem(
            id=row.get("id"),
            keyword=row.get("keyword", ""),
            difficulty_score=row.get("difficulty_score", 50),
            estimated_position=row.get("estimated_position"),
            search_volume_estimate=row.get("search_volume_estimate"),
            recommendations=row.get("recommendations", []),
            last_analyzed_at=row.get("last_analyzed_at"),
        ))

    return KeywordRankingsResponse(
        tenant_id=tenant_id,
        keywords=keywords,
    )


# ---------------------------------------------------------------------------
# Competitor Analysis
# ---------------------------------------------------------------------------


class CompetitorRequest(BaseModel):
    competitors: List[str] = Field(..., min_length=1, max_length=5, description="Competitor business names (1-5)")


@router.post("/{tenant_id}/competitor-analysis")
async def run_competitor_analysis(
    tenant_id: str,
    req: CompetitorRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI-powered competitor comparison. Analyzes your business against up to 5 competitors."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()

    # Get your business context
    tenant_result = (
        db.table("tenants")
        .select("business_name, business_type, city, website_url")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]
    business_name = tenant.get("business_name") or "Your business"
    business_type = tenant.get("business_type") or "business"
    city = tenant.get("city") or ""

    # Get your latest SEO audit score if available
    your_score = None
    try:
        audit_result = (
            db.table("seo_audits")
            .select("overall_score, categories")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if audit_result.data:
            your_score = audit_result.data[0].get("overall_score")
    except Exception:
        logger.warning("Failed to fetch SEO audit for competitor analysis")

    competitors_text = "\n".join(f"- {c}" for c in req.competitors)
    location_context = f" in {city}" if city else ""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            system=(
                "You are a local SEO and business competitive analysis expert. "
                "Analyze a business against its competitors based on your knowledge. "
                "Be specific, actionable, and honest. Use realistic scores.\n\n"
                "Return ONLY valid JSON in this exact format:\n"
                "{\n"
                '  "your_business": {"name": "...", "estimated_score": 0-100, "strengths": ["..."], "weaknesses": ["..."]},\n'
                '  "competitors": [\n'
                '    {"name": "...", "estimated_score": 0-100, "strengths": ["..."], "weaknesses": ["..."], "threat_level": "high|medium|low"}\n'
                "  ],\n"
                '  "gaps": ["actionable gap you should close"],\n'
                '  "advantages": ["things you do better than competitors"],\n'
                '  "recommendations": ["top 3-5 specific actions to outrank competitors"]\n'
                "}"
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Analyze {business_name} ({business_type}{location_context}) against these competitors:\n"
                    f"{competitors_text}\n\n"
                    f"{'My current SEO score is ' + str(your_score) + '/100. ' if your_score else ''}"
                    f"Compare online presence, likely SEO performance, review reputation, "
                    f"and local search visibility. Score each business 0-100."
                ),
            }],
        )
        raw = resp.content[0].text.strip()
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited")
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during competitor analysis")
        raise HTTPException(status_code=502, detail="AI service configuration error")
    except Exception:
        logger.exception("Competitor analysis AI call failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Competitor analysis failed")

    # Parse JSON response
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        logger.error("Failed to parse competitor analysis JSON: %s", raw[:500])
        raise HTTPException(status_code=500, detail="Failed to parse competitor analysis")

    return result
