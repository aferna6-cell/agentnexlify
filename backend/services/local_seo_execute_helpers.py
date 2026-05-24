"""Internal helpers for the local-SEO execute functions.

Extracted from ``backend/services/local_seo_execute.py`` per Rule 9 (>600
line god class). Each helper handles one slice of data loading, mutation,
or transformation that the top-level ``execute_*`` functions orchestrate.

Helpers raise ``HTTPException`` directly when failure must surface to the
client; otherwise they log and return safe defaults. The top-level
``execute_*`` functions remain in ``local_seo_execute.py`` so existing
test patches at that module path continue to work.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

logger = logging.getLogger(__name__)

__all__ = [
    "categorize_issues_by_severity",
    "upsert_keyword_rankings",
    "load_competitor_context",
    "load_seo_profile_inputs",
    "resolve_geo_inputs",
]


# ---------------------------------------------------------------------------
# execute_seo_audit
# ---------------------------------------------------------------------------


def categorize_issues_by_severity(
    categories: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Bucket issues from AI-categorized SEO audit results by severity.

    Returns (critical_issues, warnings, passed_checks). Each issue dict is
    enriched with a ``category`` key matching its parent bucket.
    """
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

    return critical_issues, warnings, passed_checks


# ---------------------------------------------------------------------------
# execute_keyword_tracking
# ---------------------------------------------------------------------------


def upsert_keyword_rankings(
    db: Any,
    tenant_id: str,
    cleaned_keywords: List[str],
    ai_lookup: Dict[str, Dict[str, Any]],
    now: str,
) -> List[Dict[str, Any]]:
    """Upsert keyword ranking rows for each cleaned keyword.

    For each keyword: if a row exists for (tenant_id, keyword), update; else
    insert. Returns saved items as dicts suitable for response construction.
    Each item is appended even if DB save fails — falls back to AI data.
    """
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
                result = db.table("keyword_rankings").insert(ranking_data).execute()
                saved = result.data[0] if result.data else ranking_data

            saved_items.append(
                {
                    "id": saved.get("id"),
                    "keyword": kw,
                    "difficulty_score": saved.get("difficulty_score", 50),
                    "estimated_position": saved.get("estimated_position"),
                    "search_volume_estimate": saved.get("search_volume_estimate"),
                    "recommendations": saved.get("recommendations", []),
                    "last_analyzed_at": saved.get("last_analyzed_at"),
                }
            )
        except Exception:
            logger.error(
                "Failed to save keyword ranking for '%s', tenant %s",
                kw,
                tenant_id,
                exc_info=True,
            )
            saved_items.append(
                {
                    "id": None,
                    "keyword": kw,
                    "difficulty_score": ranking_data["difficulty_score"],
                    "estimated_position": ranking_data["estimated_position"],
                    "search_volume_estimate": ranking_data["search_volume_estimate"],
                    "recommendations": ranking_data["recommendations"],
                    "last_analyzed_at": now,
                }
            )

    return saved_items


# ---------------------------------------------------------------------------
# execute_competitor_analysis
# ---------------------------------------------------------------------------


def load_competitor_context(
    db: Any, tenant_id: str
) -> Tuple[Dict[str, Any], Optional[int]]:
    """Load tenant info + latest audit overall_score for competitor analysis.

    Raises HTTPException 404 if tenant not found. The audit score is best-
    effort — failures log and return None.
    """
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

    your_score: Optional[int] = None
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

    return tenant, your_score


# ---------------------------------------------------------------------------
# execute_analyze_seo_profile
# ---------------------------------------------------------------------------


def load_seo_profile_inputs(
    db: Any, tenant_id: str
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], int, int, int]:
    """Load tenant + widget_config + faq/review/content counts.

    Returns (tenant, widget_config, faq_count, review_count, content_count).
    Raises HTTPException 404 if tenant not found; secondary loads are best-
    effort and return safe defaults on failure.
    """
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city, website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "Failed to load tenant %s for SEO analysis", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to load tenant data")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]

    widget_config: Optional[Dict[str, Any]] = None
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
        logger.warning(
            "Failed to load widget config for tenant %s", tenant_id, exc_info=True
        )

    faq_count = _count_table(db, "faq_entries", tenant_id, "FAQs")
    review_count = _count_table(db, "reviews", tenant_id, "reviews")
    content_count = _count_table(db, "content_items", tenant_id, "content items")

    return tenant, widget_config, faq_count, review_count, content_count


def _count_table(db: Any, table_name: str, tenant_id: str, label: str) -> int:
    """Helper — count rows for tenant in a table; log and return 0 on failure."""
    try:
        result = (
            db.table(table_name)
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.count or 0
    except Exception:
        logger.warning(
            "Failed to count %s for tenant %s", label, tenant_id, exc_info=True
        )
        return 0


# ---------------------------------------------------------------------------
# execute_geo_score
# ---------------------------------------------------------------------------


def resolve_geo_inputs(
    db: Any,
    tenant_id: str,
    business_name: Any,
    business_type: Any,
    city: Any,
    website_url: Any,
) -> Tuple[str, str, str, str, Optional[str]]:
    """Resolve GEO-scoring inputs by falling back to tenant defaults.

    Loads the tenant row; uses provided args first, then tenant values, then
    sentinel defaults. Raises HTTPException if tenant missing or business_name
    cannot be resolved. Also returns latest crawled extracted_text (best-effort).
    """
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type, city, website_url")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "Failed to load tenant %s for GEO scoring", tenant_id, exc_info=True
        )
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

    extracted_text: Optional[str] = None
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
        logger.warning(
            "Failed to load website content for GEO scoring, tenant %s",
            tenant_id,
            exc_info=True,
        )

    return business_name, business_type, city, website_url, extracted_text


# `now_iso` kept here so tests can patch a single source of "now" if desired.
def now_iso() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
