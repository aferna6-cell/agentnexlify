"""Smoke tests for backend.services.local_seo_execute + local_seo_fetch.

Exercises validation branches of the extracted service functions without
invoking Claude. Confirms error semantics are preserved across the
local_seo_handlers god-class split.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services.local_seo_execute import (
    execute_analyze_seo_profile,
    execute_competitor_analysis,
    execute_geo_score,
    execute_keyword_tracking,
    execute_seo_audit,
)
from backend.services.local_seo_fetch import (
    fetch_audit_history,
    fetch_dashboard_widget,
    fetch_keyword_rankings,
    fetch_keyword_suggestions,
    fetch_latest_audit,
    fetch_latest_geo_score,
    fetch_seo_profile,
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _build_table_chain(return_data, count=None):
    """Build a Supabase query-builder mock that resolves to the given data."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    result = MagicMock()
    result.data = return_data
    result.count = count
    chain.execute.return_value = result
    return chain


def _build_raising_chain(exc=None):
    """Build a query-builder mock whose .execute() raises — exercises except blocks."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = exc or Exception("db down")
    return chain


# ---------------------------------------------------------------------------
# execute_seo_audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_seo_audit_404_when_tenant_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Tenant not found"


@pytest.mark.asyncio
async def test_execute_seo_audit_400_when_no_crawl_content(mock_supabase):
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": None,
            }
        ]
    )
    crawl_chain = _build_table_chain([])
    mock_supabase.table.side_effect = [tenant_chain, crawl_chain]
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 400
    assert "scan your website" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_execute_seo_audit_400_when_crawl_incomplete(mock_supabase):
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": None,
            }
        ]
    )
    crawl_chain = _build_table_chain(
        [
            {
                "crawl_status": "in_progress",
                "pages_json": [],
                "extracted_text": "",
                "pages_found": 0,
            }
        ]
    )
    mock_supabase.table.side_effect = [tenant_chain, crawl_chain]
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 400
    assert "in_progress" in exc.value.detail


# ---------------------------------------------------------------------------
# execute_keyword_tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_keyword_tracking_404_when_tenant_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await execute_keyword_tracking(TENANT_ID, ["seo", "salon"])
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_execute_keyword_tracking_400_on_empty_keywords(mock_supabase):
    tenant_chain = _build_table_chain([{"business_type": "salon", "city": "NYC"}])
    mock_supabase.table.return_value = tenant_chain
    with pytest.raises(HTTPException) as exc:
        await execute_keyword_tracking(TENANT_ID, ["", "   "])
    assert exc.value.status_code == 400
    assert "no valid keywords" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_execute_keyword_tracking_returns_dicts_for_response_model(mock_supabase):
    tenant_chain = _build_table_chain([{"business_type": "salon", "city": "NYC"}])
    rankings_select = _build_table_chain([])  # no existing record → insert path
    rankings_insert = _build_table_chain(
        [
            {
                "id": "row-1",
                "tenant_id": TENANT_ID,
                "keyword": "salon nyc",
                "difficulty_score": 60,
                "estimated_position": "10-20",
                "search_volume_estimate": "medium",
                "recommendations": ["a"],
                "last_analyzed_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    # Each loop iteration calls .table() twice (select-existing, then insert)
    mock_supabase.table.side_effect = [tenant_chain, rankings_select, rankings_insert]

    with patch(
        "backend.services.local_seo_execute._analyze_keywords_ai",
        new=AsyncMock(
            return_value=[
                {
                    "keyword": "salon nyc",
                    "difficulty_score": 60,
                    "estimated_position": "10-20",
                    "search_volume_estimate": "medium",
                    "recommendations": ["a"],
                }
            ]
        ),
    ):
        items = await execute_keyword_tracking(TENANT_ID, ["salon nyc"])
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["keyword"] == "salon nyc"
    assert items[0]["id"] == "row-1"
    assert items[0]["difficulty_score"] == 60
    # Pydantic round-trip: handler output must be valid for KeywordRankingItem
    from backend.models.local_seo import KeywordRankingItem

    KeywordRankingItem(**items[0])


# ---------------------------------------------------------------------------
# execute_competitor_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_competitor_analysis_404_when_tenant_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await execute_competitor_analysis(TENANT_ID, ["Comp A"])
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Phase 4 — execute_analyze_seo_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_analyze_seo_profile_404_when_tenant_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await execute_analyze_seo_profile(TENANT_ID)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Phase 4 — fetch_seo_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_seo_profile_404_when_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await fetch_seo_profile(TENANT_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_seo_profile_returns_pydantic_compatible_dict(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {
                "id": "p1",
                "tenant_id": TENANT_ID,
                "completeness_score": 75,
                "missing_fields": [],
                "recommendations": [],
                "keyword_suggestions": [],
                "last_analyzed_at": "2026-04-27T00:00:00+00:00",
                "created_at": "2026-04-27T00:00:00+00:00",
                "updated_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    result = await fetch_seo_profile(TENANT_ID)
    from backend.models.local_seo import SEOProfileResponse

    SEOProfileResponse(**result)
    assert result["completeness_score"] == 75


# ---------------------------------------------------------------------------
# Phase 4 — fetch_keyword_suggestions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_keyword_suggestions_404_when_no_profile(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await fetch_keyword_suggestions(TENANT_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_keyword_suggestions_returns_shape(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {"keyword_suggestions": ["seo nyc", "salon nyc"]},
        ]
    )
    result = await fetch_keyword_suggestions(TENANT_ID)
    assert result == {"tenant_id": TENANT_ID, "keywords": ["seo nyc", "salon nyc"]}


# ---------------------------------------------------------------------------
# Phase 4 — fetch_dashboard_widget (never raises; logs warnings)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_dashboard_widget_empty_state(mock_supabase):
    profile_chain = _build_table_chain([])
    review_chain = _build_table_chain([], count=0)
    mock_supabase.table.side_effect = [profile_chain, review_chain]
    result = await fetch_dashboard_widget(TENANT_ID)
    from backend.models.local_seo import DashboardWidgetResponse

    DashboardWidgetResponse(**result)
    assert result == {
        "completeness_score": 0,
        "top_recommendations": [],
        "review_count": 0,
        "keyword_count": 0,
    }


@pytest.mark.asyncio
async def test_fetch_dashboard_widget_with_profile_caps_top_recommendations(
    mock_supabase,
):
    profile_chain = _build_table_chain(
        [
            {
                "completeness_score": 80,
                "recommendations": ["a", "b", "c", "d", "e"],
                "keyword_suggestions": ["k1", "k2"],
            }
        ]
    )
    review_chain = _build_table_chain([], count=7)
    mock_supabase.table.side_effect = [profile_chain, review_chain]
    result = await fetch_dashboard_widget(TENANT_ID)
    assert result["completeness_score"] == 80
    assert result["top_recommendations"] == ["a", "b", "c"]
    assert result["review_count"] == 7
    assert result["keyword_count"] == 2


# ---------------------------------------------------------------------------
# Phase 4 — fetch_latest_audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_audit_404_when_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await fetch_latest_audit(TENANT_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_latest_audit_returns_pydantic_compatible_dict(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {
                "id": "a1",
                "tenant_id": TENANT_ID,
                "overall_score": 65,
                "categories": {},
                "critical_issues": [],
                "warnings": [],
                "passed_checks": [],
                "recommendations": [],
                "pages_analyzed": 5,
                "created_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    result = await fetch_latest_audit(TENANT_ID)
    from backend.models.local_seo import SEOAuditResponse

    SEOAuditResponse(**result)
    assert result["overall_score"] == 65


# ---------------------------------------------------------------------------
# Phase 4 — fetch_audit_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_audit_history_empty(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    result = await fetch_audit_history(TENANT_ID, days=30)
    assert result == {"tenant_id": TENANT_ID, "audits": [], "days": 30}


@pytest.mark.asyncio
async def test_fetch_audit_history_aggregates_severity_counts(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {
                "id": "a1",
                "overall_score": 70,
                "pages_analyzed": 4,
                "critical_issues": [{"x": 1}, {"x": 2}],
                "warnings": [{"x": 1}],
                "passed_checks": [{"x": 1}, {"x": 2}, {"x": 3}],
                "created_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    result = await fetch_audit_history(TENANT_ID, days=30)
    assert result["days"] == 30
    assert len(result["audits"]) == 1
    a = result["audits"][0]
    assert a["critical_count"] == 2
    assert a["warning_count"] == 1
    assert a["passed_count"] == 3


# ---------------------------------------------------------------------------
# Phase 4 — execute_geo_score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_geo_score_404_when_tenant_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await execute_geo_score(TENANT_ID, None, None, None, None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_execute_geo_score_400_when_business_name_missing(mock_supabase):
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": None,
                "business_type": None,
                "city": None,
                "website_url": None,
            }
        ]
    )
    mock_supabase.table.return_value = tenant_chain
    with pytest.raises(HTTPException) as exc:
        await execute_geo_score(TENANT_ID, None, None, None, None)
    assert exc.value.status_code == 400
    assert "business name" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# Phase 4 — fetch_latest_geo_score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_geo_score_404_when_missing(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    with pytest.raises(HTTPException) as exc:
        await fetch_latest_geo_score(TENANT_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_latest_geo_score_returns_pydantic_compatible_dict(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {
                "id": "g1",
                "tenant_id": TENANT_ID,
                "overall_score": 55,
                "platform_scores": {},
                "visibility_factors": [],
                "recommendations": [],
                "created_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    result = await fetch_latest_geo_score(TENANT_ID)
    from backend.models.local_seo import GEOScoreResponse

    GEOScoreResponse(**result)
    assert result["overall_score"] == 55


# ---------------------------------------------------------------------------
# Phase 4 — fetch_keyword_rankings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_keyword_rankings_empty(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain([])
    result = await fetch_keyword_rankings(TENANT_ID)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_keyword_rankings_returns_pydantic_compatible_list(mock_supabase):
    mock_supabase.table.return_value = _build_table_chain(
        [
            {
                "id": "r1",
                "keyword": "salon nyc",
                "difficulty_score": 60,
                "estimated_position": "10-20",
                "search_volume_estimate": "medium",
                "recommendations": ["x"],
                "last_analyzed_at": "2026-04-27T00:00:00+00:00",
            }
        ]
    )
    rows = await fetch_keyword_rankings(TENANT_ID)
    from backend.models.local_seo import KeywordRankingItem

    [KeywordRankingItem(**r) for r in rows]
    assert len(rows) == 1
    assert rows[0]["keyword"] == "salon nyc"


# ===========================================================================
# Error-path coverage — DB failures map to HTTP 500 / logged warnings.
# Each fetch_/execute_ except branch is exercised below.
# ===========================================================================


# --- local_seo_fetch.py — DB failure → HTTP 500 -----------------------------


@pytest.mark.asyncio
async def test_fetch_seo_profile_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_seo_profile(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch SEO profile"


@pytest.mark.asyncio
async def test_fetch_keyword_suggestions_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_keyword_suggestions(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch keyword suggestions"


@pytest.mark.asyncio
async def test_fetch_dashboard_widget_swallows_db_errors(mock_supabase):
    """Both queries fail — widget never raises, returns safe defaults."""
    mock_supabase.table.side_effect = [_build_raising_chain(), _build_raising_chain()]
    result = await fetch_dashboard_widget(TENANT_ID)
    assert result == {
        "completeness_score": 0,
        "top_recommendations": [],
        "review_count": 0,
        "keyword_count": 0,
    }


@pytest.mark.asyncio
async def test_fetch_latest_audit_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_latest_audit(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch SEO audit"


@pytest.mark.asyncio
async def test_fetch_audit_history_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_audit_history(TENANT_ID, days=30)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch audit history"


@pytest.mark.asyncio
async def test_fetch_latest_geo_score_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_latest_geo_score(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch GEO score"


@pytest.mark.asyncio
async def test_fetch_keyword_rankings_500_on_db_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await fetch_keyword_rankings(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch keyword rankings"


# --- local_seo_execute.py — tenant/crawl load failures → HTTP 500 -----------


@pytest.mark.asyncio
async def test_execute_seo_audit_500_on_tenant_load_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to load tenant data"


@pytest.mark.asyncio
async def test_execute_seo_audit_500_on_crawl_load_error(mock_supabase):
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": None,
            }
        ]
    )
    mock_supabase.table.side_effect = [tenant_chain, _build_raising_chain()]
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to load website content"


@pytest.mark.asyncio
async def test_execute_seo_audit_happy_path_non_int_score_and_save(mock_supabase):
    """Full audit: non-integer AI score coerces to 0, insert result is returned."""
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": "https://biz.example",
            }
        ]
    )
    crawl_chain = _build_table_chain(
        [
            {
                "crawl_status": "completed",
                "pages_json": [{"url": "/"}],
                "extracted_text": "homepage copy",
                "pages_found": 3,
            }
        ]
    )
    audit_insert = _build_table_chain(
        [{"id": "audit-1", "created_at": "2026-04-27T00:00:00+00:00"}]
    )
    mock_supabase.table.side_effect = [tenant_chain, crawl_chain, audit_insert]

    audit_ai_result = {
        "overall_score": "not-a-number",
        "categories": {
            "meta": {
                "issues": [
                    {"severity": "critical", "title": "missing title"},
                    {"severity": "warning", "title": "thin content"},
                    {"severity": "passed", "title": "has h1"},
                ]
            }
        },
        "recommendations": ["fix titles"],
    }
    with patch(
        "backend.services.local_seo_execute._run_seo_audit_ai",
        new=AsyncMock(return_value=audit_ai_result),
    ):
        result = await execute_seo_audit(TENANT_ID)

    assert result["id"] == "audit-1"
    assert result["overall_score"] == 0  # non-int coerced
    assert result["pages_analyzed"] == 3
    assert len(result["critical_issues"]) == 1
    assert len(result["warnings"]) == 1
    assert len(result["passed_checks"]) == 1


@pytest.mark.asyncio
async def test_execute_keyword_tracking_500_on_tenant_load_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await execute_keyword_tracking(TENANT_ID, ["salon nyc"])
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to load tenant data"


@pytest.mark.asyncio
async def test_execute_keyword_tracking_save_failure_falls_back_to_ai_data(
    mock_supabase,
):
    """DB save error per keyword → handler still returns the AI-computed row."""
    tenant_chain = _build_table_chain([{"business_type": "salon", "city": "NYC"}])
    mock_supabase.table.side_effect = [tenant_chain, _build_raising_chain()]

    with patch(
        "backend.services.local_seo_execute._analyze_keywords_ai",
        new=AsyncMock(
            return_value=[
                {
                    "keyword": "salon nyc",
                    "difficulty_score": 60,
                    "estimated_position": "10-20",
                    "search_volume_estimate": "medium",
                    "recommendations": ["a"],
                }
            ]
        ),
    ):
        items = await execute_keyword_tracking(TENANT_ID, ["salon nyc"])

    assert len(items) == 1
    assert items[0]["id"] is None  # save failed → no DB id
    assert items[0]["keyword"] == "salon nyc"
    assert items[0]["difficulty_score"] == 60


@pytest.mark.asyncio
async def test_execute_competitor_analysis_500_on_parse_failure(mock_supabase):
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": None,
            }
        ]
    )
    audit_chain = _build_table_chain([])
    mock_supabase.table.side_effect = [tenant_chain, audit_chain]

    with patch(
        "backend.services.local_seo_execute.call_claude_messages",
        new=AsyncMock(return_value=MagicMock(text="this is not json")),
    ):
        with pytest.raises(HTTPException) as exc:
            await execute_competitor_analysis(TENANT_ID, ["Comp A"])
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to parse competitor analysis"


@pytest.mark.asyncio
async def test_execute_analyze_seo_profile_500_on_tenant_load_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await execute_analyze_seo_profile(TENANT_ID)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to load tenant data"


@pytest.mark.asyncio
async def test_execute_analyze_seo_profile_swallows_count_and_save_errors(
    mock_supabase,
):
    """Widget/FAQ/review/content count failures + profile save failure are
    logged, not raised — analysis still returns a profile dict."""
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": "https://biz.example",
            }
        ]
    )
    # tenant ok, then widget/faq/reviews/content + seo_profiles select all fail
    mock_supabase.table.side_effect = [
        tenant_chain,
        _build_raising_chain(),
        _build_raising_chain(),
        _build_raising_chain(),
        _build_raising_chain(),
        _build_raising_chain(),
    ]

    with patch(
        "backend.services.local_seo_execute._generate_keywords",
        new=AsyncMock(return_value=["salon nyc"]),
    ):
        result = await execute_analyze_seo_profile(TENANT_ID)

    assert result["tenant_id"] == TENANT_ID
    assert result["id"] is None  # save failed
    assert isinstance(result["completeness_score"], int)


@pytest.mark.asyncio
async def test_execute_geo_score_500_on_tenant_load_error(mock_supabase):
    mock_supabase.table.return_value = _build_raising_chain()
    with pytest.raises(HTTPException) as exc:
        await execute_geo_score(TENANT_ID, None, None, None, None)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to load tenant data"


@pytest.mark.asyncio
async def test_execute_geo_score_happy_path_non_int_score_and_save(mock_supabase):
    """Website-content load failure is swallowed; non-int AI score coerces to 0;
    geo_scores insert result is returned."""
    tenant_chain = _build_table_chain(
        [
            {
                "business_name": "Biz",
                "business_type": "salon",
                "city": "NYC",
                "website_url": "https://biz.example",
            }
        ]
    )
    geo_insert = _build_table_chain(
        [{"id": "geo-1", "created_at": "2026-04-27T00:00:00+00:00"}]
    )
    # tenant ok, website_content load fails (swallowed), geo_scores insert ok
    mock_supabase.table.side_effect = [tenant_chain, _build_raising_chain(), geo_insert]

    geo_ai_result = {
        "overall_score": "bad-value",
        "platform_scores": {},
        "visibility_factors": [],
        "recommendations": [],
    }
    with patch(
        "backend.services.local_seo_execute._run_geo_score_ai",
        new=AsyncMock(return_value=geo_ai_result),
    ):
        result = await execute_geo_score(TENANT_ID, None, None, None, None)

    assert result["id"] == "geo-1"
    assert result["overall_score"] == 0  # non-int coerced
