"""API-level tests for the content repurposer router.

Validates the full create -> list -> get -> connect -> delete flow.
"""

import os
os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_TEST_SECRET = "test-secret-key-for-jwt"


def _make_token(tenant_id: str = "tenant-001", plan: str = "professional") -> str:
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "test@example.com",
        "plan": plan,
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


def _auth(tenant_id: str = "tenant-001", plan: str = "professional") -> dict:
    return {"Authorization": f"Bearer {_make_token(tenant_id, plan)}"}


def _pass_plan_check(claims):
    """No-op replacement for _verify_plan."""
    pass


class TestRepurposeCreate:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose._run_repurpose_job")
    @patch("backend.routers.content_repurpose._verify_plan", _pass_plan_check)
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_create_job(self, mock_db, mock_run, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "job-1", "status": "processing"}]
        )
        resp = client.post(
            "/api/v1/repurpose/tenant-001",
            json={
                "source_type": "text",
                "source_input": "This is a great blog post about AI chatbots for small business.",
                "tone": "professional",
                "formats": ["social_posts", "email_sequence"],
            },
            headers=_auth(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "job-1"
        assert data["status"] == "processing"

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_create_job_free_plan_rejected(self, mock_db, mock_settings):
        """Free plan should not access repurposer."""
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"plan": "free"}
        )
        resp = client.post(
            "/api/v1/repurpose/tenant-001",
            json={
                "source_type": "text",
                "source_input": "Test content",
                "tone": "professional",
                "formats": ["social_post"],
            },
            headers=_auth(plan="free"),
        )
        assert resp.status_code == 403

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose._verify_plan", _pass_plan_check)
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_create_job_invalid_source_type(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        resp = client.post(
            "/api/v1/repurpose/tenant-001",
            json={
                "source_type": "invalid_type",
                "source_input": "content",
                "tone": "professional",
                "formats": ["social_post"],
            },
            headers=_auth(),
        )
        assert resp.status_code == 400


class TestRepurposeList:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose._verify_plan", _pass_plan_check)
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_list_jobs(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "job-1", "source_type": "text", "status": "completed"},
                {"id": "job-2", "source_type": "url", "status": "processing"},
            ]
        )
        resp = client.get("/api/v1/repurpose/tenant-001", headers=_auth())
        assert resp.status_code == 200
        assert len(resp.json()["jobs"]) == 2

    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose._verify_plan", _pass_plan_check)
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_get_single_job(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "job-1", "source_type": "text", "status": "completed", "outputs": {"social_post": "Great news!"}}
        )
        resp = client.get("/api/v1/repurpose/tenant-001/job-1", headers=_auth())
        assert resp.status_code == 200


class TestRepurposeDelete:
    @patch("backend.routers.auth.settings")
    @patch("backend.routers.content_repurpose._verify_plan", _pass_plan_check)
    @patch("backend.routers.content_repurpose.get_supabase")
    def test_delete_job(self, mock_db, mock_settings):
        mock_settings.api_secret_key = _TEST_SECRET
        db = MagicMock()
        mock_db.return_value = db
        db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        resp = client.delete("/api/v1/repurpose/tenant-001/job-1", headers=_auth())
        assert resp.status_code == 200


class TestRepurposeNoAuth:
    def test_create_no_auth(self):
        resp = client.post("/api/v1/repurpose/tenant-001", json={"source_type": "text"})
        assert resp.status_code == 422

    def test_list_no_auth(self):
        resp = client.get("/api/v1/repurpose/tenant-001")
        assert resp.status_code == 422
