"""Tests for platform admin analytics and promotions endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.main import app

ADMIN_SECRET = "test-secret-key-12345"


@pytest.fixture(autouse=True)
def patch_admin_secret():
    """Patch the admin secret in all admin modules."""
    with patch("backend.routers.admin_analytics.settings") as mock_s, \
         patch("backend.routers.admin_promotions.settings") as mock_ps:
        mock_s.api_secret_key = ADMIN_SECRET
        mock_ps.api_secret_key = ADMIN_SECRET
        yield


def make_admin_request(client, path, method="GET", body=None):
    """Helper to make authenticated admin requests."""
    kwargs = {"headers": {"x-api-secret": ADMIN_SECRET}}
    if body:
        kwargs["json"] = body
        kwargs["method"] = method.upper()
    return getattr(client, method.lower())(f"/api/v1/admin{path}", **kwargs)


class TestAdminOverview:
    def test_overview_requires_secret(self):
        """No header and no fallback secret should return 401."""
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/overview")
            assert res.status_code == 401

    def test_overview_wrong_secret(self):
        client = TestClient(app)
        res = client.get("/api/v1/admin/overview", headers={"x-api-secret": "wrong-secret"})
        assert res.status_code == 401


class TestAdminPlanDistribution:
    def test_plan_distribution_requires_secret(self):
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/plan-distribution")
            assert res.status_code == 401


class TestAdminTenants:
    def test_tenants_requires_secret(self):
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/tenants")
            assert res.status_code == 401


class TestAdminIndustryBreakdown:
    def test_industry_breakdown_requires_secret(self):
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/industry-breakdown")
            assert res.status_code == 401


class TestAdminPromotions:
    def test_list_promotions_requires_secret(self):
        with patch("backend.routers.admin_promotions.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/promotions")
            assert res.status_code == 401

    def test_create_promotion_invalid_type(self):
        client = TestClient(app)
        res = client.post("/api/v1/admin/promotions", headers={"x-api-secret": ADMIN_SECRET}, json={
            "tenant_id": "test-tenant-id",
            "promotion_type": "invalid_type",
        })
        assert res.status_code == 400

    def test_create_promotion_missing_fields(self):
        client = TestClient(app)
        res = client.post("/api/v1/admin/promotions", headers={"x-api-secret": ADMIN_SECRET}, json={})
        assert res.status_code == 422  # Pydantic validation


class TestAdminRevenueTrends:
    def test_revenue_trends_requires_secret(self):
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/revenue-trends")
            assert res.status_code == 401


class TestAdminMonthlyGrowth:
    def test_monthly_growth_requires_secret(self):
        with patch("backend.routers.admin_analytics.settings") as mock_s:
            mock_s.api_secret_key = None
            client = TestClient(app)
            res = client.get("/api/v1/admin/monthly-growth")
            assert res.status_code == 401
