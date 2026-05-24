"""Write/compute operations for local SEO — the five execute_ functions.

Extracted from backend/services/local_seo_handlers.py per Rule 9
(>600 line god class). Each function orchestrates AI analysis + DB writes.
Pure functions return plain dict/list — Pydantic construction happens at
the router boundary.

Each function raises HTTPException directly on validation/AI/DB failure;
FastAPI handles the exception at any layer in the call stack.
"""

import json
import logging
from datetime import datetime, timezone
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
from backend.services.local_seo_execute_helpers import (  # noqa: F401
    categorize_issues_by_severity,
    load_competitor_context,
    load_seo_profile_inputs,
    resolve_geo_inputs,
    upsert_keyword_rankings,
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
        logger.error(
            "Failed to load website content for tenant %s", tenant_id, exc_info=True
        )
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
        pages_json,
        extracted_text,
        business_name,
        business_type,
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
        logger.warning(
            "AI returned non-integer overall_score: %s",
            audit_result.get("overall_score"),
        )
        overall_score = 0
    categories = audit_result.get("categories", {})
    recommendations_list = audit_result.get("recommendations", [])

    critical_issues, warnings, passed_checks = categorize_issues_by_severity(categories)

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
        insert_result = db.table("seo_audits").insert(audit_data).execute()
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
    tenant_id: str,
    keywords: List[str],
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
        logger.error(
            "Failed to load tenant %s for keyword tracking", tenant_id, exc_info=True
        )
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
    return upsert_keyword_rankings(db, tenant_id, cleaned_keywords, ai_lookup, now)


async def execute_competitor_analysis(
    tenant_id: str,
    competitors: List[str],
) -> Dict[str, Any]:
    """AI-powered competitor comparison. Returns parsed JSON dict.

    Raises HTTPException for tenant-not-found, AI failure, parse failure.
    """
    db = get_service_supabase()

    tenant, your_score = load_competitor_context(db, tenant_id)
    business_name = tenant.get("business_name") or "Your business"
    business_type = tenant.get("business_type") or "business"
    city = tenant.get("city") or ""

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
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze {business_name} ({business_type}{location_context}) against these competitors:\n"
                        f"{competitors_text}\n\n"
                        f"{'My current SEO score is ' + str(your_score) + '/100. ' if your_score else ''}"
                        f"Compare online presence, likely SEO performance, review reputation, "
                        f"and local search visibility. Score each business 0-100."
                    ),
                }
            ],
            metadata={
                "tenant_id": tenant_id,
                "business_name": business_name,
                "competitor_count": len(competitors),
            },
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
        raise HTTPException(
            status_code=500, detail="Failed to parse competitor analysis"
        )


async def execute_analyze_seo_profile(tenant_id: str) -> Dict[str, Any]:
    """Compute SEO completeness, generate keywords, upsert seo_profiles."""
    db = get_service_supabase()

    tenant, widget_config, faq_count, review_count, content_count = (
        load_seo_profile_inputs(db, tenant_id)
    )

    score, missing, recommendations = _calculate_completeness(
        tenant,
        widget_config,
        faq_count,
        review_count,
        content_count,
    )

    keywords = await _generate_keywords(
        tenant.get("business_type"),
        tenant.get("city"),
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
            result = db.table("seo_profiles").insert(profile_data).execute()

        saved = result.data[0] if result.data else profile_data
    except Exception:
        logger.error(
            "Failed to save SEO profile for tenant %s", tenant_id, exc_info=True
        )
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


async def execute_geo_score(
    tenant_id: str,
    business_name: Any,
    business_type: Any,
    city: Any,
    website_url: Any,
) -> Dict[str, Any]:
    """Calculate GEO visibility score using Claude AI; persist to geo_scores."""
    db = get_service_supabase()

    business_name, business_type, city, website_url, extracted_text = resolve_geo_inputs(
        db, tenant_id, business_name, business_type, city, website_url
    )

    geo_result = await _run_geo_score_ai(
        business_name,
        business_type,
        city,
        website_url,
        extracted_text,
    )

    if not geo_result:
        raise HTTPException(
            status_code=500,
            detail="GEO analysis could not be completed. Please try again.",
        )

    try:
        overall_score = int(geo_result.get("overall_score") or 0)
    except (TypeError, ValueError):
        logger.warning(
            "AI returned non-integer GEO overall_score: %s",
            geo_result.get("overall_score"),
        )
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
        insert_result = db.table("geo_scores").insert(geo_data).execute()
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
