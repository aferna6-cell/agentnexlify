"""Read-only operations for the local SEO service layer.

Contains the seven fetch_ functions that query the database and return
dicts ready for Pydantic response model construction at the router boundary.
No AI calls, no writes.

Each function raises HTTPException directly on DB failure or not-found;
FastAPI handles the exception at any layer in the call stack.

Split from backend/services/local_seo_handlers.py per Rule 9 (god class
>600 lines).  Write/compute operations live in local_seo_execute.py.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import HTTPException

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


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
        logger.error(
            "Failed to fetch SEO profile for tenant %s", tenant_id, exc_info=True
        )
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
        raise HTTPException(
            status_code=500, detail="Failed to fetch keyword suggestions"
        )

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
    recommendations: list = []
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
        logger.warning(
            "Failed to load SEO profile for dashboard widget, tenant %s",
            tenant_id,
            exc_info=True,
        )

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
        logger.warning(
            "Failed to count reviews for dashboard widget, tenant %s",
            tenant_id,
            exc_info=True,
        )

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
        logger.error(
            "Failed to fetch SEO audit for tenant %s", tenant_id, exc_info=True
        )
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
            .select(
                "id, overall_score, pages_analyzed, critical_issues, warnings, passed_checks, created_at"
            )
            .eq("tenant_id", tenant_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
    except Exception:
        logger.error(
            "Failed to fetch audit history for tenant %s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to fetch audit history")

    audits: List[Dict[str, Any]] = []
    for audit in result.data or []:
        critical_list = audit.get("critical_issues", [])
        warning_list = audit.get("warnings", [])
        passed_list = audit.get("passed_checks", [])
        audits.append(
            {
                "id": audit["id"],
                "overall_score": audit.get("overall_score", 0),
                "pages_analyzed": audit.get("pages_analyzed", 0),
                "critical_count": (
                    len(critical_list) if isinstance(critical_list, list) else 0
                ),
                "warning_count": (
                    len(warning_list) if isinstance(warning_list, list) else 0
                ),
                "passed_count": (
                    len(passed_list) if isinstance(passed_list, list) else 0
                ),
                "created_at": audit.get("created_at"),
            }
        )

    return {"tenant_id": tenant_id, "audits": audits, "days": days}


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
        logger.error(
            "Failed to fetch GEO score for tenant %s", tenant_id, exc_info=True
        )
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
        logger.error(
            "Failed to fetch keyword rankings for tenant %s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to fetch keyword rankings")

    rows: List[Dict[str, Any]] = []
    for row in result.data or []:
        rows.append(
            {
                "id": row.get("id"),
                "keyword": row.get("keyword", ""),
                "difficulty_score": row.get("difficulty_score", 50),
                "estimated_position": row.get("estimated_position"),
                "search_volume_estimate": row.get("search_volume_estimate"),
                "recommendations": row.get("recommendations", []),
                "last_analyzed_at": row.get("last_analyzed_at"),
            }
        )

    return rows
