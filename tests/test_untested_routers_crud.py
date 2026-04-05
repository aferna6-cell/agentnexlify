"""Tests for previously untested CRUD routers.

Covers: snippets, tag_definitions, scoring_config, email_templates,
custom_fields, pipeline_automations, waitlist, wizard_analytics, csat,
smart_lists, bids.
"""

import os
os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


def _make_token(tenant_id: str = "tenant-001") -> str:
    from jose import jwt

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


def _auth(tenant_id: str = "tenant-001") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


def _mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# Snippets
# ---------------------------------------------------------------------------


class TestSnippets:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.snippets.get_supabase")
    def test_list_snippets(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "s1", "title": "Hello", "content": "Hi there", "shortcut": "/hi"}]
        )
        resp = client.get("/api/v1/snippets/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.snippets.get_supabase")
    def test_create_snippet(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "s2", "title": "Thanks", "content": "Thank you!", "shortcut": "/ty"}]
        )
        resp = client.post(
            "/api/v1/snippets/tenant-001",
            json={"title": "Thanks", "content": "Thank you!", "shortcut": "/ty"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    def test_snippets_no_auth_returns_422(self):
        resp = client.get("/api/v1/snippets/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tag Definitions
# ---------------------------------------------------------------------------


class TestTagDefinitions:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.tag_definitions.get_supabase")
    def test_list_tags(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "t1", "tag_name": "VIP", "tag_color": "#ff0000"}]
        )
        resp = client.get("/api/v1/tags/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.tag_definitions.get_supabase")
    def test_create_tag(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "t2", "tag_name": "New", "tag_color": "#00ff00"}]
        )
        resp = client.post(
            "/api/v1/tags/tenant-001",
            json={"tag_name": "New", "tag_color": "#00ff00"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    def test_tags_no_auth_returns_422(self):
        resp = client.get("/api/v1/tags/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Scoring Config
# ---------------------------------------------------------------------------


class TestScoringConfig:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.scoring_config.get_supabase")
    def test_list_scoring_factors(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "f1", "factor": "email", "weight": 20}]
        )
        resp = client.get("/api/v1/scoring/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.scoring_config.get_supabase")
    def test_create_scoring_factor(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "f2", "factor": "phone", "weight": 15}]
        )
        resp = client.post(
            "/api/v1/scoring/tenant-001",
            json={"factor": "phone", "weight": 15},
            headers=_auth(),
        )
        assert resp.status_code == 200

    def test_scoring_no_auth_returns_422(self):
        resp = client.get("/api/v1/scoring/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Email Templates
# ---------------------------------------------------------------------------


class TestEmailTemplates:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.email_templates.get_supabase")
    def test_list_templates(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "et1", "name": "Welcome", "subject_template": "Hi {{name}}"}]
        )
        resp = client.get("/api/v1/email-templates/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.email_templates.get_supabase")
    def test_create_template(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "et2", "name": "Follow-up", "subject_template": "Following up"}]
        )
        resp = client.post(
            "/api/v1/email-templates/tenant-001",
            json={"name": "Follow-up", "subject_template": "Following up", "body_template": "<p>Hi</p>"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    def test_email_templates_no_auth_returns_422(self):
        resp = client.get("/api/v1/email-templates/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Custom Fields
# ---------------------------------------------------------------------------


class TestCustomFields:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.custom_fields.get_supabase")
    def test_list_fields(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "cf1", "field_name": "company_size", "field_type": "number"}]
        )
        resp = client.get("/api/v1/custom-fields/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.custom_fields.get_supabase")
    def test_create_field(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        # Mock both count queries (duplicate check + sort_order) and insert
        dup_check = MagicMock(count=0)
        count_result = MagicMock(count=3)
        insert_result = MagicMock(data=[{"id": "cf2", "field_name": "industry", "field_type": "text"}])
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = dup_check
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        db.table.return_value.insert.return_value.execute.return_value = insert_result
        resp = client.post(
            "/api/v1/custom-fields/tenant-001",
            json={"field_name": "industry", "field_type": "text"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    def test_custom_fields_no_auth_returns_422(self):
        resp = client.get("/api/v1/custom-fields/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pipeline Automations
# ---------------------------------------------------------------------------


class TestPipelineAutomations:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.pipeline_automations.get_supabase")
    def test_list_automations(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "pa1", "name": "Auto-email on Won", "trigger_stage": "Won"}]
        )
        resp = client.get("/api/v1/pipeline/tenant-001/automations", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.pipeline_automations.get_supabase")
    def test_create_automation(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "pa2", "name": "Notify on Lost", "trigger_stage": "Lost"}]
        )
        resp = client.post(
            "/api/v1/pipeline/tenant-001/automations",
            json={"name": "Notify on Lost", "trigger_stage": "Lost", "actions": [{"type": "notify_team", "message": "Deal lost"}]},
            headers=_auth(),
        )
        assert resp.status_code == 201

    def test_pipeline_automations_no_auth_returns_422(self):
        resp = client.get("/api/v1/pipeline/tenant-001/automations")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------


class TestWaitlist:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.waitlist.get_supabase")
    def test_list_waitlist(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "w1", "customer_name": "Jane", "status": "waiting"}]
        )
        resp = client.get("/api/v1/waitlist/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.waitlist.get_supabase")
    def test_public_waitlist_join(self, mock_db):
        """Public endpoint — no auth needed, uses api_key."""
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"tenant_id": "tenant-001"}
        )
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "w2", "customer_name": "Bob", "status": "waiting"}]
        )
        resp = client.post(
            "/api/v1/waitlist/public/test-api-key",
            json={
                "customer_name": "Bob",
                "customer_email": "bob@test.com",
                "preferred_date": "2026-04-10",
            },
        )
        assert resp.status_code == 200

    def test_waitlist_no_auth_returns_422(self):
        resp = client.get("/api/v1/waitlist/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Wizard Analytics
# ---------------------------------------------------------------------------


class TestWizardAnalytics:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.wizard_analytics.get_supabase")
    def test_post_event(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        resp = client.post(
            "/api/v1/wizard/tenant-001/event",
            json={"step": 2, "action": "complete"},
            headers=_auth(),
        )
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.wizard_analytics.get_supabase")
    def test_get_stats(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"step": 1, "action": "complete"}]
        )
        resp = client.get("/api/v1/wizard/tenant-001/stats", headers=_auth())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# CSAT
# ---------------------------------------------------------------------------


class TestCSAT:
    @patch("backend.routers.csat.get_supabase")
    def test_submit_csat(self, mock_db):
        """Public endpoint — token format is tenant_id:session_id."""
        db = _mock_db()
        mock_db.return_value = db
        # Mock duplicate check (count=0)
        dup_result = MagicMock(count=0)
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = dup_result
        # Mock conversation lookup
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "c1"}])
        resp = client.post(
            "/api/v1/csat/submit",
            json={"token": "tenant-001:sess-123", "rating": 5, "feedback": "Great!"},
        )
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.csat.get_supabase")
    def test_csat_stats(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"rating": 5, "created_at": "2026-04-05T10:00:00Z", "feedback": "Great"},
                {"rating": 4, "created_at": "2026-04-05T11:00:00Z", "feedback": None},
            ]
        )
        resp = client.get("/api/v1/csat/tenant-001/stats", headers=_auth())
        assert resp.status_code == 200

    def test_csat_stats_no_auth_returns_422(self):
        resp = client.get("/api/v1/csat/tenant-001/stats")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Smart Lists
# ---------------------------------------------------------------------------


class TestSmartLists:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.smart_lists.get_supabase")
    def test_list_smart_lists(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "sl1", "name": "Hot Leads", "filters_json": {"status": "hot"}}]
        )
        resp = client.get("/api/v1/smart-lists/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.smart_lists.get_supabase")
    def test_create_smart_list(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "sl2", "name": "Cold Leads", "filters_json": {"status": "cold"}}]
        )
        resp = client.post(
            "/api/v1/smart-lists/tenant-001",
            json={"name": "Cold Leads", "filters_json": {"status": "cold"}},
            headers=_auth(),
        )
        assert resp.status_code == 201

    def test_smart_lists_no_auth_returns_422(self):
        resp = client.get("/api/v1/smart-lists/tenant-001")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bids
# ---------------------------------------------------------------------------


class TestBids:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.bids.get_supabase")
    def test_list_bids(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "b1", "title": "Roof Repair", "total": 5000, "status": "draft"}]
        )
        resp = client.get("/api/v1/bids/tenant-001", headers=_auth())
        assert resp.status_code == 200

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.bids.get_supabase")
    def test_create_bid(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = _mock_db()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "b2", "title": "Deck Build", "total": 8000, "status": "draft"}]
        )
        resp = client.post(
            "/api/v1/bids/tenant-001",
            json={
                "title": "Deck Build",
                "items_json": [{"description": "Labor", "quantity": 1, "unit": "job", "unit_price": 8000, "total": 8000}],
            },
            headers=_auth(),
        )
        assert resp.status_code == 201

    def test_bids_no_auth_returns_422(self):
        resp = client.get("/api/v1/bids/tenant-001")
        assert resp.status_code == 422
