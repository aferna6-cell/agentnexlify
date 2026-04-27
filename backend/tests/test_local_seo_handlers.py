"""Smoke tests for backend.services.local_seo_handlers.

Phase 2 refactor verification — exercises validation branches of the three
extracted service functions without invoking Claude. Confirms the orchestration
moved cleanly from routers/local_seo.py and that error semantics are preserved.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services.local_seo_handlers import (
    execute_competitor_analysis,
    execute_keyword_tracking,
    execute_seo_audit,
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _build_table_chain(return_data):
    """Build a Supabase query-builder mock that resolves to the given data."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    result = MagicMock()
    result.data = return_data
    chain.execute.return_value = result
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
    tenant_chain = _build_table_chain([{"business_name": "Biz", "business_type": "salon", "city": "NYC", "website_url": None}])
    crawl_chain = _build_table_chain([])
    mock_supabase.table.side_effect = [tenant_chain, crawl_chain]
    with pytest.raises(HTTPException) as exc:
        await execute_seo_audit(TENANT_ID)
    assert exc.value.status_code == 400
    assert "scan your website" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_execute_seo_audit_400_when_crawl_incomplete(mock_supabase):
    tenant_chain = _build_table_chain([{"business_name": "Biz", "business_type": "salon", "city": "NYC", "website_url": None}])
    crawl_chain = _build_table_chain([{"crawl_status": "in_progress", "pages_json": [], "extracted_text": "", "pages_found": 0}])
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
    rankings_insert = _build_table_chain([{
        "id": "row-1",
        "tenant_id": TENANT_ID,
        "keyword": "salon nyc",
        "difficulty_score": 60,
        "estimated_position": "10-20",
        "search_volume_estimate": "medium",
        "recommendations": ["a"],
        "last_analyzed_at": "2026-04-27T00:00:00+00:00",
    }])
    # Each loop iteration calls .table() twice (select-existing, then insert)
    mock_supabase.table.side_effect = [tenant_chain, rankings_select, rankings_insert]

    with patch(
        "backend.services.local_seo_handlers._analyze_keywords_ai",
        new=AsyncMock(return_value=[{
            "keyword": "salon nyc",
            "difficulty_score": 60,
            "estimated_position": "10-20",
            "search_volume_estimate": "medium",
            "recommendations": ["a"],
        }]),
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
