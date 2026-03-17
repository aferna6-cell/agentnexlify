"""Tests for Social Media Marketing and Campaign endpoints."""

import os
os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


def _make_token(tenant_id: str = "tenant-001") -> str:
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": "professional",
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth_header(tenant_id: str = "tenant-001") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


# ---------------------------------------------------------------------------
# Social Posts CRUD
# ---------------------------------------------------------------------------


class TestSocialPostsCRUD:
    """Test social media post create/list."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.social_media.get_supabase")
    def test_create_post(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "post-1", "platform": "twitter", "content": "Hello!", "status": "draft"}]
        )

        resp = client.post(
            "/api/v1/social/tenant-001/posts",
            json={"platform": "twitter", "content": "Hello!", "hashtags": ["#test"]},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        assert resp.json()["platform"] == "twitter"

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.social_media.get_supabase")
    def test_list_posts(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "post-1", "platform": "twitter", "content": "Hello!"}],
            count=1,
        )

        resp = client.get(
            "/api/v1/social/tenant-001/posts",
            headers=_auth_header(),
        )
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    def test_create_post_invalid_platform(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        resp = client.post(
            "/api/v1/social/tenant-001/posts",
            json={"platform": "tiktok", "content": "Hello!"},
            headers=_auth_header(),
        )
        assert resp.status_code == 400

    def test_no_auth_returns_error(self):
        resp = client.post(
            "/api/v1/social/tenant-001/posts",
            json={"platform": "twitter", "content": "Hello!"},
        )
        assert resp.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# AI Content Generation
# ---------------------------------------------------------------------------


class TestAIGeneration:
    """Test AI content generation endpoints."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.social_media.get_supabase")
    @patch("backend.routers.social_media.anthropic")
    def test_generate_content(self, mock_anthropic, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"business_name": "Test Biz", "business_type": "plumber"}
        )

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Great plumbing tips!\nHASHTAGS: #plumbing #local")]
        )

        resp = client.post(
            "/api/v1/social/tenant-001/generate",
            json={"topic": "spring plumbing tips", "platform": "twitter"},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert "character_count" in data
        assert data["platform"] == "twitter"


# ---------------------------------------------------------------------------
# Marketing Campaigns
# ---------------------------------------------------------------------------


class TestMarketingCampaigns:
    """Test marketing campaign CRUD."""

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.marketing_campaigns.get_supabase")
    def test_create_email_campaign(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "camp-1", "name": "Spring Sale", "type": "email", "status": "draft"}]
        )

        resp = client.post(
            "/api/v1/campaigns/tenant-001",
            json={
                "name": "Spring Sale",
                "type": "email",
                "subject": "Spring Sale!",
                "body": "<p>50% off all services</p>",
            },
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Spring Sale"

    @patch("backend.routers.auth.settings")
    def test_create_campaign_invalid_type(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        resp = client.post(
            "/api/v1/campaigns/tenant-001",
            json={"name": "Bad", "type": "fax", "body": "Hello"},
            headers=_auth_header(),
        )
        assert resp.status_code == 400

    @patch("backend.routers.auth.settings")
    def test_email_campaign_requires_subject(self, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        resp = client.post(
            "/api/v1/campaigns/tenant-001",
            json={"name": "No Subject", "type": "email", "body": "<p>Content</p>"},
            headers=_auth_header(),
        )
        assert resp.status_code == 400

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.marketing_campaigns._query_target_leads")
    def test_estimate_recipients(self, mock_query, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        mock_query.return_value = [
            {"id": "lead-1", "email": "a@b.com"},
            {"id": "lead-2", "email": "c@d.com"},
        ]

        resp = client.post(
            "/api/v1/campaigns/tenant-001/estimate",
            json={},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        assert resp.json()["estimated_recipients"] == 2

    def test_no_auth_returns_error(self):
        resp = client.get("/api/v1/campaigns/tenant-001")
        assert resp.status_code in (401, 403, 422)
