"""Local SEO Tools endpoints — profile completeness, SEO audit, GEO scoring, keyword tracking.

Route bodies delegate to backend.services.local_seo_handlers (Phases 2 + 4).
Pydantic models live in backend.models.local_seo (Phase 3).
"""

import logging

from fastapi import APIRouter, Depends, Query

from backend.dependencies import _get_current_tenant
from backend.models.local_seo import (
    CompetitorRequest,
    DashboardWidgetResponse,
    GEOScoreRequest,
    GEOScoreResponse,
    KeywordRankingItem,
    KeywordRankingsResponse,
    KeywordTrackRequest,
    SEOAuditResponse,
    SEOProfileResponse,
)
from backend.services.addon_gate import require_marketing_addon
from backend.services.local_seo_handlers import (
    execute_analyze_seo_profile,
    execute_competitor_analysis,
    execute_geo_score,
    execute_keyword_tracking,
    execute_seo_audit,
    fetch_audit_history,
    fetch_dashboard_widget,
    fetch_keyword_rankings,
    fetch_keyword_suggestions,
    fetch_latest_audit,
    fetch_latest_geo_score,
    fetch_seo_profile,
)
from backend.services.local_seo_scoring import _verify_tenant

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/seo",
    tags=["local-seo"],
    dependencies=[Depends(require_marketing_addon)],
)


# ---------------------------------------------------------------------------
# SEO Profile + Dashboard Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/analyze", response_model=SEOProfileResponse)
async def analyze_seo_profile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Analyze the tenant's profile for SEO completeness and generate keyword suggestions."""
    _verify_tenant(claims, tenant_id)
    result = await execute_analyze_seo_profile(tenant_id)
    return SEOProfileResponse(**result)


@router.get("/{tenant_id}", response_model=SEOProfileResponse)
async def get_seo_profile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the cached SEO profile for a tenant."""
    _verify_tenant(claims, tenant_id)
    result = await fetch_seo_profile(tenant_id)
    return SEOProfileResponse(**result)


@router.get("/{tenant_id}/keywords")
async def get_keyword_suggestions(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get keyword suggestions from the cached SEO profile."""
    _verify_tenant(claims, tenant_id)
    return await fetch_keyword_suggestions(tenant_id)


@router.get("/{tenant_id}/dashboard-widget", response_model=DashboardWidgetResponse)
async def get_dashboard_widget(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Return a summary card for the main dashboard."""
    _verify_tenant(claims, tenant_id)
    result = await fetch_dashboard_widget(tenant_id)
    return DashboardWidgetResponse(**result)


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
    result = await fetch_latest_audit(tenant_id)
    return SEOAuditResponse(**result)


@router.get("/{tenant_id}/audit/history")
async def get_audit_history(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=90),
    claims: dict = Depends(_get_current_tenant),
):
    """Get SEO audit history for the last N days (default 30)."""
    _verify_tenant(claims, tenant_id)
    return await fetch_audit_history(tenant_id, days)


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
    result = await execute_geo_score(
        tenant_id,
        body.business_name,
        body.business_type,
        body.city,
        body.website_url,
    )
    return GEOScoreResponse(**result)


@router.get("/{tenant_id}/geo-score", response_model=GEOScoreResponse)
async def get_latest_geo_score(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get the latest GEO visibility score for a tenant."""
    _verify_tenant(claims, tenant_id)
    result = await fetch_latest_geo_score(tenant_id)
    return GEOScoreResponse(**result)


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
    rows = await fetch_keyword_rankings(tenant_id)
    return KeywordRankingsResponse(
        tenant_id=tenant_id,
        keywords=[KeywordRankingItem(**row) for row in rows],
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
