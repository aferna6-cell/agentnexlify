"""Local SEO Tools endpoints — profile completeness, SEO audit, GEO scoring, keyword tracking."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.database import get_service_supabase
from backend.models.local_seo import (
    CompetitorRequest,
    DashboardWidgetResponse,
    GEOScoreRequest,
    GEOScoreResponse,
    KeywordRankingItem,
    KeywordRankingsResponse,
    KeywordTrackRequest,
    SEOAuditHistoryItem,
    SEOAuditResponse,
    SEOCategoryScore,
    SEOIssue,
    SEOProfileResponse,
)
from backend.dependencies import _get_current_tenant
from backend.services.addon_gate import require_marketing_addon
from backend.services.local_seo_ai import (
    _generate_keywords,
    _run_geo_score_ai,
)
from backend.services.local_seo_handlers import (
    execute_competitor_analysis,
    execute_keyword_tracking,
    execute_seo_audit,
)
from backend.services.local_seo_scoring import (
    _calculate_completeness,
    _verify_tenant,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/seo",
    tags=["local-seo"],
    dependencies=[Depends(require_marketing_addon)],
)


# ---------------------------------------------------------------------------
# Pydantic models — extracted to backend/models/local_seo.py
# Helpers — extracted to backend/services/local_seo_scoring.py
# ---------------------------------------------------------------------------


# AI runners extracted to backend/services/local_seo_ai.py


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

    db = get_service_supabase()

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


@router.get("/{tenant_id}/dashboard-widget", response_model=DashboardWidgetResponse)
async def get_dashboard_widget(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return a summary card for the main dashboard."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
    result = await execute_seo_audit(tenant_id)
    return SEOAuditResponse(**result)


@router.get("/{tenant_id}/audit", response_model=SEOAuditResponse)
async def get_latest_audit(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the latest SEO audit results for a tenant."""
    _verify_tenant(claims, tenant_id)

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

    db = get_service_supabase()

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
    items = await execute_keyword_tracking(tenant_id, body.keywords)
    return KeywordRankingsResponse(
        tenant_id=tenant_id,
        keywords=[KeywordRankingItem(**item) for item in items],
    )


@router.get("/{tenant_id}/keywords/rankings", response_model=KeywordRankingsResponse)
async def get_keyword_rankings(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get all tracked keyword rankings for a tenant."""
    _verify_tenant(claims, tenant_id)

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


@router.post("/{tenant_id}/competitor-analysis")
async def run_competitor_analysis(
    tenant_id: str,
    req: CompetitorRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """AI-powered competitor comparison. Analyzes your business against up to 5 competitors."""
    _verify_tenant(claims, tenant_id)
    return await execute_competitor_analysis(tenant_id, req.competitors)
