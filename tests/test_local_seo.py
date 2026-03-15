"""Tests for the Local SEO Tools endpoints."""

import os
os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(tenant_id: str = "tenant-001") -> str:
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": "growth",
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth_header(tenant_id: str = "tenant-001") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name."""
    def mock_table(name):
        data, count = table_responses.get(name, ([], None))

        table = MagicMock()
        for method in [
            "select", "insert", "update", "delete",
            "eq", "neq", "gte", "lte", "gt", "lt",
            "limit", "order", "ilike", "range",
            "in_", "is_", "or_", "contains",
        ]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = data
        result.count = count if count is not None else len(data)
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


# ---------------------------------------------------------------------------
# POST /{tenant_id}/analyze
# ---------------------------------------------------------------------------


class TestAnalyzeSEO:
    """Tests for POST /api/v1/seo/{tenant_id}/analyze."""

    @patch("backend.routers.local_seo._generate_keywords")
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_analyze_full_profile(self, mock_db, mock_settings, mock_keywords):
        mock_settings.api_secret_key = _TEST_SECRET
        mock_keywords.return_value = ["plumber in Austin", "emergency plumber Austin TX"]

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "tenants": (
                [{"business_name": "Acme Plumbing", "business_type": "plumbing",
                  "city": "Austin", "website_url": "https://acme.com"}],
                1,
            ),
            "widget_configs": (
                [{"greeting_message": "Hello!", "booking_enabled": True}],
                1,
            ),
            "faq_entries": ([], 10),
            "reviews": ([], 5),
            "content_items": ([], 3),
            "seo_profiles": ([], 0),
        })

        resp = client.post(
            "/api/v1/seo/tenant-001/analyze",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["completeness_score"] == 100
        assert data["missing_fields"] == []
        assert data["keyword_suggestions"] == ["plumber in Austin", "emergency plumber Austin TX"]

    @patch("backend.routers.local_seo._generate_keywords")
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_analyze_empty_profile(self, mock_db, mock_settings, mock_keywords):
        mock_settings.api_secret_key = _TEST_SECRET
        mock_keywords.return_value = []

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "tenants": (
                [{"business_name": None, "business_type": None,
                  "city": None, "website_url": None}],
                1,
            ),
            "widget_configs": ([], 0),
            "faq_entries": ([], 0),
            "reviews": ([], 0),
            "content_items": ([], 0),
            "seo_profiles": ([], 0),
        })

        resp = client.post(
            "/api/v1/seo/tenant-001/analyze",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["completeness_score"] == 0
        assert "business_name" in data["missing_fields"]
        assert "city" in data["missing_fields"]
        assert "website_url" in data["missing_fields"]
        assert "business_type" in data["missing_fields"]
        assert len(data["recommendations"]) > 0

    @patch("backend.routers.local_seo._generate_keywords")
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_analyze_partial_profile(self, mock_db, mock_settings, mock_keywords):
        mock_settings.api_secret_key = _TEST_SECRET
        mock_keywords.return_value = ["dentist in Denver"]

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "tenants": (
                [{"business_name": "Denver Dental", "business_type": "dental",
                  "city": "Denver", "website_url": None}],
                1,
            ),
            "widget_configs": (
                [{"greeting_message": None, "booking_enabled": False}],
                1,
            ),
            "faq_entries": ([], 3),
            "reviews": ([], 0),
            "content_items": ([], 0),
            "seo_profiles": ([], 0),
        })

        resp = client.post(
            "/api/v1/seo/tenant-001/analyze",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        # business_name=10 + city=10 + business_type=10 + faq=3/10*15=4
        assert data["completeness_score"] == 34
        assert "website_url" in data["missing_fields"]
        assert "reviews" in data["missing_fields"]
        assert "booking_enabled" in data["missing_fields"]

    @patch("backend.routers.local_seo._generate_keywords")
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_analyze_updates_existing_profile(self, mock_db, mock_settings, mock_keywords):
        """When a profile already exists, it should update (not insert)."""
        mock_settings.api_secret_key = _TEST_SECRET
        mock_keywords.return_value = []

        mock_client = MagicMock()
        mock_db.return_value = mock_client

        # Track which methods get called
        call_log = []

        def mock_table(name):
            table = MagicMock()
            for method in [
                "select", "insert", "update", "delete",
                "eq", "neq", "gte", "lte", "gt", "lt",
                "limit", "order", "ilike", "range",
                "in_", "is_", "or_", "contains",
            ]:
                getattr(table, method).return_value = table

            if name == "tenants":
                result = MagicMock()
                result.data = [{"business_name": "Test", "business_type": None,
                                "city": None, "website_url": None}]
                result.count = 1
                table.execute.return_value = result
            elif name == "seo_profiles":
                # First call (select) returns existing, subsequent calls return update result
                results = iter([
                    MagicMock(data=[{"id": "existing-profile-id"}], count=1),
                    MagicMock(data=[{"id": "existing-profile-id", "tenant_id": "tenant-001"}], count=1),
                ])
                table.execute.side_effect = lambda: next(results)
            else:
                result = MagicMock()
                result.data = []
                result.count = 0
                table.execute.return_value = result

            return table

        mock_client.table = mock_table

        resp = client.post(
            "/api/v1/seo/tenant-001/analyze",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    def test_analyze_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.post(
            "/api/v1/seo/tenant-002/analyze",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403

    @patch("backend.routers.local_seo._generate_keywords")
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_analyze_tenant_not_found(self, mock_db, mock_settings, mock_keywords):
        mock_settings.api_secret_key = _TEST_SECRET
        mock_keywords.return_value = []

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "tenants": ([], 0),
        })

        resp = client.post(
            "/api/v1/seo/tenant-001/analyze",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /{tenant_id}
# ---------------------------------------------------------------------------


class TestGetSEOProfile:
    """Tests for GET /api/v1/seo/{tenant_id}."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_get_profile_success(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "seo_profiles": (
                [{
                    "id": "profile-001",
                    "tenant_id": "tenant-001",
                    "completeness_score": 75,
                    "missing_fields": ["reviews"],
                    "recommendations": ["Collect reviews"],
                    "keyword_suggestions": ["plumber Austin"],
                    "last_analyzed_at": "2026-03-15T10:00:00Z",
                    "created_at": "2026-03-15T09:00:00Z",
                    "updated_at": "2026-03-15T10:00:00Z",
                }],
                1,
            ),
        })

        resp = client.get(
            "/api/v1/seo/tenant-001",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["completeness_score"] == 75
        assert data["missing_fields"] == ["reviews"]
        assert data["keyword_suggestions"] == ["plumber Austin"]

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_get_profile_not_found(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "seo_profiles": ([], 0),
        })

        resp = client.get(
            "/api/v1/seo/tenant-001",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 404
        assert "Run an analysis first" in resp.json()["detail"]

    @patch("backend.routers.auth.settings")
    def test_get_profile_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/seo/tenant-002",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /{tenant_id}/keywords
# ---------------------------------------------------------------------------


class TestGetKeywords:
    """Tests for GET /api/v1/seo/{tenant_id}/keywords."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_get_keywords_success(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "seo_profiles": (
                [{"keyword_suggestions": ["plumber Austin", "emergency plumber"]}],
                1,
            ),
        })

        resp = client.get(
            "/api/v1/seo/tenant-001/keywords",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["keywords"] == ["plumber Austin", "emergency plumber"]
        assert data["tenant_id"] == "tenant-001"

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_get_keywords_no_profile(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "seo_profiles": ([], 0),
        })

        resp = client.get(
            "/api/v1/seo/tenant-001/keywords",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 404

    @patch("backend.routers.auth.settings")
    def test_get_keywords_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/seo/tenant-002/keywords",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /{tenant_id}/dashboard-widget
# ---------------------------------------------------------------------------


class TestDashboardWidget:
    """Tests for GET /api/v1/seo/{tenant_id}/dashboard-widget."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_dashboard_widget_with_profile(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client

        def mock_table(name):
            table = MagicMock()
            for method in [
                "select", "insert", "update", "delete",
                "eq", "neq", "gte", "lte", "gt", "lt",
                "limit", "order", "ilike", "range",
                "in_", "is_", "or_", "contains",
            ]:
                getattr(table, method).return_value = table

            if name == "seo_profiles":
                result = MagicMock()
                result.data = [{
                    "completeness_score": 65,
                    "recommendations": ["Add FAQs", "Enable booking", "Collect reviews", "Add website"],
                    "keyword_suggestions": ["plumber Austin", "drain cleaning", "pipe repair"],
                }]
                result.count = 1
                table.execute.return_value = result
            elif name == "reviews":
                result = MagicMock()
                result.data = []
                result.count = 7
                table.execute.return_value = result
            else:
                result = MagicMock()
                result.data = []
                result.count = 0
                table.execute.return_value = result

            return table

        mock_client.table = mock_table

        resp = client.get(
            "/api/v1/seo/tenant-001/dashboard-widget",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["completeness_score"] == 65
        assert len(data["top_recommendations"]) == 3
        assert data["top_recommendations"] == ["Add FAQs", "Enable booking", "Collect reviews"]
        assert data["review_count"] == 7
        assert data["keyword_count"] == 3

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.local_seo.get_supabase")
    def test_dashboard_widget_no_profile(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        mock_client = MagicMock()
        mock_db.return_value = mock_client
        _setup_table_mock(mock_client, {
            "seo_profiles": ([], 0),
            "reviews": ([], 0),
        })

        resp = client.get(
            "/api/v1/seo/tenant-001/dashboard-widget",
            headers=_auth_header("tenant-001"),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["completeness_score"] == 0
        assert data["top_recommendations"] == []
        assert data["review_count"] == 0
        assert data["keyword_count"] == 0

    @patch("backend.routers.auth.settings")
    def test_dashboard_widget_unauthorized(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET

        resp = client.get(
            "/api/v1/seo/tenant-002/dashboard-widget",
            headers=_auth_header("tenant-001"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Completeness scoring unit tests
# ---------------------------------------------------------------------------


class TestCompletenessCalculation:
    """Unit tests for the _calculate_completeness helper."""

    def test_perfect_score(self):
        from backend.routers.local_seo import _calculate_completeness

        score, missing, recs = _calculate_completeness(
            tenant={"business_name": "Test", "business_type": "plumbing",
                    "city": "Austin", "website_url": "https://test.com"},
            widget_config={"greeting_message": "Hello!", "booking_enabled": True},
            faq_count=10,
            review_count=5,
            content_count=3,
        )

        assert score == 100
        assert missing == []
        assert recs == []

    def test_zero_score(self):
        from backend.routers.local_seo import _calculate_completeness

        score, missing, recs = _calculate_completeness(
            tenant={"business_name": None, "business_type": None,
                    "city": None, "website_url": None},
            widget_config=None,
            faq_count=0,
            review_count=0,
            content_count=0,
        )

        assert score == 0
        assert len(missing) == 9
        assert len(recs) == 9

    def test_faq_scaling(self):
        from backend.routers.local_seo import _calculate_completeness

        # 5 FAQs = 5/10 * 15 = 7.5 -> 7
        score_5, _, _ = _calculate_completeness(
            tenant={"business_name": None, "business_type": None,
                    "city": None, "website_url": None},
            widget_config=None,
            faq_count=5,
            review_count=0,
            content_count=0,
        )
        assert score_5 == 7

        # 10+ FAQs = full 15 pts
        score_10, _, _ = _calculate_completeness(
            tenant={"business_name": None, "business_type": None,
                    "city": None, "website_url": None},
            widget_config=None,
            faq_count=15,
            review_count=0,
            content_count=0,
        )
        assert score_10 == 15

    def test_widget_no_greeting_no_booking(self):
        from backend.routers.local_seo import _calculate_completeness

        score, missing, _ = _calculate_completeness(
            tenant={"business_name": "Test", "business_type": None,
                    "city": None, "website_url": None},
            widget_config={"greeting_message": None, "booking_enabled": False},
            faq_count=0,
            review_count=0,
            content_count=0,
        )

        assert "widget_greeting" in missing
        assert "booking_enabled" in missing
        # business_name = 10, rest missing
        assert score == 10
