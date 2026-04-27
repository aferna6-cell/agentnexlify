"""Service layer for local SEO route handlers.

Orchestration extracted from backend/routers/local_seo.py per User Rule 9
(>600 line god class). Pure functions return plain dict/list — Pydantic
response model construction happens at the router boundary.

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
    _run_seo_audit_ai,
)
from backend.services.local_seo_scoring import _parse_json_object_response

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
