"""Service layer for local SEO route handlers.

Orchestration extracted from backend/routers/local_seo.py per User Rule 9
(>600 line god class). Pure functions return plain dict/list — Pydantic
response model construction happens at the router boundary.

Each function raises HTTPException directly on validation/AI/DB failure;
FastAPI handles the exception at any layer in the call stack.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import anthropic
from fastapi import HTTPException

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.local_seo_ai import (
    _analyze_keywords_ai,
    _generate_keywords,
    _run_geo_score_ai,
    _run_seo_audit_ai,
)
from backend.services.local_seo_scoring import (
    _calculate_completeness,
    _parse_json_object_response,
)

logger = logging.getLogger(__name__)


async def execute_seo_audit(tenant_id: str) -> Dict[str, Any]:
    """Run full SEO audit using crawled website content + Claude analysis.

    Returns dict ready for SEOAuditResponse(**result) construction.
    Raises HTTPException for tenant-not-found, missing-crawl, or AI failure.
    """
    db = get_service_supabase()

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
    critical_issues: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    passed_checks: List[Dict[str, Any]] = []

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

    pages_analyzed = pages_found if isinstance(pages_found, int) else len(pages_json)

    audit_data = {
        "tenant_id": tenant_id,
        "overall_score": overall_score,
        "categories": categories,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "passed_checks": passed_checks,
        "recommendations": recommendations_list,
        "pages_analyzed": pages_analyzed,
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

    return {
        "id": saved.get("id"),
        "tenant_id": tenant_id,
        "overall_score": overall_score,
        "categories": categories,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "passed_checks": passed_checks,
        "recommendations": recommendations_list,
        "pages_analyzed": pages_analyzed,
        "created_at": saved.get("created_at"),
    }


async def execute_keyword_tracking(
    tenant_id: str, keywords: List[str],
) -> List[Dict[str, Any]]:
    """Add keywords to track + analyze competitiveness via Claude.

    Returns list of dicts ready for KeywordRankingItem(**d) construction.
    Raises HTTPException for tenant-not-found, empty-keywords.
    """
    db = get_service_supabase()

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
    cleaned_keywords = list(set(kw.strip().lower() for kw in keywords if kw.strip()))
    if not cleaned_keywords:
        raise HTTPException(status_code=400, detail="No valid keywords provided")

    # Run AI analysis
    analysis_results = await _analyze_keywords_ai(cleaned_keywords, business_type, city)

    # Build a lookup from the AI results
    ai_lookup: Dict[str, Dict[str, Any]] = {}
    for item in analysis_results:
        if isinstance(item, dict) and "keyword" in item:
            ai_lookup[item["keyword"].lower()] = item

    now = datetime.now(timezone.utc).isoformat()
    saved_items: List[Dict[str, Any]] = []

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

            saved_items.append({
                "id": saved.get("id"),
                "keyword": kw,
                "difficulty_score": saved.get("difficulty_score", 50),
                "estimated_position": saved.get("estimated_position"),
                "search_volume_estimate": saved.get("search_volume_estimate"),
                "recommendations": saved.get("recommendations", []),
                "last_analyzed_at": saved.get("last_analyzed_at"),
            })
        except Exception:
            logger.error("Failed to save keyword ranking for '%s', tenant %s", kw, tenant_id, exc_info=True)
            # Still include the keyword with AI data even if DB save fails
            saved_items.append({
                "id": None,
                "keyword": kw,
                "difficulty_score": ranking_data["difficulty_score"],
                "estimated_position": ranking_data["estimated_position"],
                "search_volume_estimate": ranking_data["search_volume_estimate"],
                "recommendations": ranking_data["recommendations"],
                "last_analyzed_at": now,
            })

    return saved_items


async def execute_competitor_analysis(
    tenant_id: str, competitors: List[str],
) -> Dict[str, Any]:
    """AI-powered competitor comparison. Returns parsed JSON dict.

    Raises HTTPException for tenant-not-found, AI failure, parse failure.
    """
    db = get_service_supabase()

    # Get business context
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

    # Latest SEO audit score (optional context for the prompt)
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

    competitors_text = "\n".join(f"- {c}" for c in competitors)
    location_context = f" in {city}" if city else ""

    try:
        resp = await call_claude_messages(
            operation="seo.competitor_analysis",
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            timeout=60.0,
            max_retries=1,
            retry_delay_seconds=1.0,
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
            metadata={"tenant_id": tenant_id, "business_name": business_name, "competitor_count": len(competitors)},
        )
        raw = resp.text.strip()
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
        return _parse_json_object_response(raw)
    except (json.JSONDecodeError, ValueError, IndexError):
        logger.error("Failed to parse competitor analysis JSON: %s", raw[:500])
        raise HTTPException(status_code=500, detail="Failed to parse competitor analysis")


# ---------------------------------------------------------------------------
# Phase 4 handlers — extracted from remaining inline route bodies
# ---------------------------------------------------------------------------


async def execute_analyze_seo_profile(tenant_id: str) -> Dict[str, Any]:
    """Compute SEO completeness, generate keywords, upsert seo_profiles."""
    db = get_service_supabase()

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

    score, missing, recommendations = _calculate_completeness(
        tenant, widget_config, faq_count, review_count, content_count,
    )

    keywords = await _generate_keywords(
        tenant.get("business_type"), tenant.get("city"),
    )

    now = datetime.now(timezone.utc).isoformat()

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
        saved = profile_data

    return {
        "id": saved.get("id"),
        "tenant_id": tenant_id,
        "completeness_score": score,
        "missing_fields": missing,
        "recommendations": recommendations,
        "keyword_suggestions": keywords,
        "last_analyzed_at": now,
        "created_at": saved.get("created_at"),
        "updated_at": saved.get("updated_at", now),
    }


async def fetch_seo_profile(tenant_id: str) -> Dict[str, Any]:
    """Get cached SEO profile."""
    db = get_service_supabase()

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
    return {
        "id": profile.get("id"),
        "tenant_id": profile.get("tenant_id", tenant_id),
        "completeness_score": profile.get("completeness_score", 0),
        "missing_fields": profile.get("missing_fields", []),
        "recommendations": profile.get("recommendations", []),
        "keyword_suggestions": profile.get("keyword_suggestions", []),
        "last_analyzed_at": profile.get("last_analyzed_at"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }


async def fetch_keyword_suggestions(tenant_id: str) -> Dict[str, Any]:
    """Get keyword suggestions from cached SEO profile."""
    db = get_service_supabase()

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


async def fetch_dashboard_widget(tenant_id: str) -> Dict[str, Any]:
    """Summary card data for main dashboard."""
    db = get_service_supabase()

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

    return {
        "completeness_score": completeness_score,
        "top_recommendations": recommendations,
        "review_count": review_count,
        "keyword_count": keyword_count,
    }


async def fetch_latest_audit(tenant_id: str) -> Dict[str, Any]:
    """Get latest SEO audit results."""
    db = get_service_supabase()

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
    return {
        "id": audit.get("id"),
        "tenant_id": audit.get("tenant_id", tenant_id),
        "overall_score": audit.get("overall_score", 0),
        "categories": audit.get("categories", {}),
        "critical_issues": audit.get("critical_issues", []),
        "warnings": audit.get("warnings", []),
        "passed_checks": audit.get("passed_checks", []),
        "recommendations": audit.get("recommendations", []),
        "pages_analyzed": audit.get("pages_analyzed", 0),
        "created_at": audit.get("created_at"),
    }


async def fetch_audit_history(tenant_id: str, days: int) -> Dict[str, Any]:
    """Get SEO audit history for last N days."""
    db = get_service_supabase()
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

    audits: List[Dict[str, Any]] = []
    for audit in (result.data or []):
        critical_list = audit.get("critical_issues", [])
        warning_list = audit.get("warnings", [])
        passed_list = audit.get("passed_checks", [])
        audits.append({
            "id": audit["id"],
            "overall_score": audit.get("overall_score", 0),
            "pages_analyzed": audit.get("pages_analyzed", 0),
            "critical_count": len(critical_list) if isinstance(critical_list, list) else 0,
            "warning_count": len(warning_list) if isinstance(warning_list, list) else 0,
            "passed_count": len(passed_list) if isinstance(passed_list, list) else 0,
            "created_at": audit.get("created_at"),
        })

    return {"tenant_id": tenant_id, "audits": audits, "days": days}


async def execute_geo_score(
    tenant_id: str,
    business_name: Any,
    business_type: Any,
    city: Any,
    website_url: Any,
) -> Dict[str, Any]:
    """Calculate GEO visibility score using Claude AI; persist to geo_scores."""
    db = get_service_supabase()

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

    business_name = business_name or tenant.get("business_name") or "Unknown Business"
    business_type = business_type or tenant.get("business_type") or "local business"
    city = city or tenant.get("city") or "unknown"
    website_url = website_url or tenant.get("website_url") or ""

    if not business_name or business_name == "Unknown Business":
        raise HTTPException(
            status_code=400,
            detail="Business name is required. Set it in your profile or provide it in the request.",
        )

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

    return {
        "id": saved.get("id"),
        "tenant_id": tenant_id,
        "overall_score": overall_score,
        "platform_scores": platform_scores,
        "visibility_factors": visibility_factors,
        "recommendations": recommendations_list,
        "created_at": saved.get("created_at"),
    }


async def fetch_latest_geo_score(tenant_id: str) -> Dict[str, Any]:
    """Get latest GEO visibility score."""
    db = get_service_supabase()

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
    return {
        "id": geo.get("id"),
        "tenant_id": geo.get("tenant_id", tenant_id),
        "overall_score": geo.get("overall_score", 0),
        "platform_scores": geo.get("platform_scores", {}),
        "visibility_factors": geo.get("visibility_factors", []),
        "recommendations": geo.get("recommendations", []),
        "created_at": geo.get("created_at"),
    }


async def fetch_keyword_rankings(tenant_id: str) -> List[Dict[str, Any]]:
    """Get all tracked keyword rankings."""
    db = get_service_supabase()

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

    rows: List[Dict[str, Any]] = []
    for row in (result.data or []):
        rows.append({
            "id": row.get("id"),
            "keyword": row.get("keyword", ""),
            "difficulty_score": row.get("difficulty_score", 50),
            "estimated_position": row.get("estimated_position"),
            "search_volume_estimate": row.get("search_volume_estimate"),
            "recommendations": row.get("recommendations", []),
            "last_analyzed_at": row.get("last_analyzed_at"),
        })

    return rows
