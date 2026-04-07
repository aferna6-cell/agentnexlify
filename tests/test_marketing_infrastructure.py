"""End-to-end tests for marketing infrastructure: campaigns, analytics, A/B tests, automation rules."""

import json
import time
import hmac
import hashlib
import base64
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from backend.main import app
from backend.routers.auth import _get_current_tenant

TEST_SECRET = "test-secret-key-for-jwt"
TEST_TENANT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(tenant_id: str = TEST_TENANT_ID, role: str = "owner", secret: str = TEST_SECRET) -> str:
    """Create a minimal JWT for testing (HS256)."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "tenant_id": tenant_id,
        "role": role,
        "exp": int(time.time()) + 3600,
    }).encode())
    sig_input = f"{header}.{payload}".encode()
    sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


@pytest.fixture
def auth_headers():
    """Return JWT auth headers."""
    return {"Authorization": f"Bearer {_make_jwt()}"}


@pytest.fixture
def tenant_override():
    """Override tenant auth dependency for all requests."""
    app.dependency_overrides[_get_current_tenant] = lambda: {
        "tenant_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "role": "owner",
        "plan": "growth",
        "is_team_member": False,
    }
    yield
    app.dependency_overrides.pop(_get_current_tenant, None)


@pytest.fixture(autouse=True)
def mock_supabase(mock_supabase):
    """Use global mock_supabase fixture + patch router-level imports.

    Routers use `from backend.models.database import get_supabase` which
    creates a local binding. The conftest patches the module, but we also
    need to patch each router's local reference.
    """
    with patch("backend.routers.marketing_campaigns.get_supabase", return_value=mock_supabase), \
         patch("backend.routers.marketing_analytics.get_supabase", return_value=mock_supabase), \
         patch("backend.routers.ab_tests.get_supabase", return_value=mock_supabase), \
         patch("backend.routers.automation_rules.get_supabase", return_value=mock_supabase):
        yield mock_supabase


# ─── Marketing Campaigns ─────────────────────────────────────────────────────


class TestMarketingCampaigns:
    def test_create_campaign_success(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [{"id": "camp-1", "name": "Summer Sale", "type": "email", "status": "draft"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Summer Sale",
            "type": "email",
            "subject": "Hot deals!",
            "body": "<p>Check this out</p>",
        })
        assert res.status_code == 200
        assert res.json()["name"] == "Summer Sale"

    def test_create_campaign_missing_subject_for_email(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Email Campaign",
            "type": "email",
            "body": "<p>No subject</p>",
        })
        assert res.status_code == 400

    def test_create_campaign_sms_no_subject_required(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [{"id": "camp-sms", "type": "sms"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "SMS Blast",
            "type": "sms",
            "body": "Hey there!",
        })
        assert res.status_code == 200

    def test_create_campaign_invalid_type(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Bad Campaign",
            "type": "push_notification",
            "body": "test",
        })
        assert res.status_code == 400

    def test_list_campaigns(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [{"id": "c1"}, {"id": "c2"}], count=2)
        client = TestClient(app)
        res = client.get(f"/api/v1/campaigns/{TEST_TENANT_ID}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "campaigns" in data
        assert "total" in data

    def test_get_campaign_not_found(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [])
        client = TestClient(app)
        res = client.get(f"/api/v1/campaigns/{TEST_TENANT_ID}/nonexistent", headers=auth_headers)
        assert res.status_code == 404

    def test_update_campaign_block_sent_status(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.put(f"/api/v1/campaigns/{TEST_TENANT_ID}/camp-1", headers=auth_headers, json={
            "status": "sent"
        })
        assert res.status_code == 400

    def test_generate_campaign_email_invalid_type(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}/generate-email", headers=auth_headers, json={
            "topic": "test",
            "campaign_type": "invalid_type",
        })
        assert res.status_code == 400

    def test_send_campaign_already_sent(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [{"id": "camp-1", "status": "sent"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}/camp-1/send", headers=auth_headers)
        assert res.status_code == 400

    def test_send_campaign_already_sending(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [{"id": "camp-1", "status": "sending"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/campaigns/{TEST_TENANT_ID}/camp-1/send", headers=auth_headers)
        assert res.status_code == 400


# ─── Marketing Analytics ─────────────────────────────────────────────────────


class TestMarketingAnalytics:
    def test_dashboard(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [])
        client = TestClient(app)
        res = client.get(f"/api/v1/marketing/{TEST_TENANT_ID}/dashboard", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_campaigns" in data
        assert "avg_open_rate" in data

    def test_trends_30d(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [])
        mock_supabase.set_table_data("campaign_sends", [])
        client = TestClient(app)
        res = client.get(f"/api/v1/marketing/{TEST_TENANT_ID}/trends?period=30d", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "trends" in data
        assert data["period"] == "30d"

    def test_trends_90d(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("marketing_campaigns", [])
        mock_supabase.set_table_data("campaign_sends", [])
        client = TestClient(app)
        res = client.get(f"/api/v1/marketing/{TEST_TENANT_ID}/trends?period=90d", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["period"] == "90d"


# ─── A/B Tests ────────────────────────────────────────────────────────────────


class TestABTests:
    def test_create_ab_test_success(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("ab_tests", [{"id": "test-1", "name": "Subject Test", "status": "draft"}])
        mock_supabase.set_table_data("ab_test_variants", [{"id": "v1"}, {"id": "v2"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Subject Test",
            "test_type": "subject_line",
            "variants": [
                {"name": "Variant A", "allocation_percent": 50},
                {"name": "Variant B", "allocation_percent": 50},
            ],
        })
        assert res.status_code == 200
        assert res.json()["name"] == "Subject Test"

    def test_create_ab_test_allocation_must_sum_100(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Bad Allocation",
            "test_type": "subject_line",
            "variants": [
                {"name": "A", "allocation_percent": 30},
                {"name": "B", "allocation_percent": 30},
            ],
        })
        assert res.status_code == 400

    def test_create_ab_test_invalid_type(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Bad Type",
            "test_type": "invalid_xyz",
            "variants": [
                {"name": "A", "allocation_percent": 50},
                {"name": "B", "allocation_percent": 50},
            ],
        })
        assert res.status_code == 400

    def test_create_ab_test_too_few_variants(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "One Variant",
            "test_type": "subject_line",
            "variants": [{"name": "A", "allocation_percent": 100}],
        })
        assert res.status_code == 422  # Pydantic validation: min_length=2

    def test_list_ab_tests(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("ab_tests", [], count=0)
        client = TestClient(app)
        res = client.get(f"/api/v1/ab-tests/{TEST_TENANT_ID}", headers=auth_headers)
        assert res.status_code == 200

    def test_start_ab_test_wrong_status(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("ab_tests", [{"id": "test-1", "status": "completed"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}/test-1/start", headers=auth_headers)
        assert res.status_code == 400

    def test_pause_ab_test_wrong_status(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("ab_tests", [{"id": "test-1", "status": "draft"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/ab-tests/{TEST_TENANT_ID}/test-1/pause", headers=auth_headers)
        assert res.status_code == 400

    def test_delete_ab_test(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("ab_tests", [{"id": "test-1"}])
        client = TestClient(app)
        res = client.delete(f"/api/v1/ab-tests/{TEST_TENANT_ID}/test-1", headers=auth_headers)
        assert res.status_code == 204


# ─── Automation Rules ─────────────────────────────────────────────────────────


class TestAutomationRules:
    def test_create_rule_success(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("automation_rules", [{"id": "rule-1", "name": "Auto Follow-up", "trigger_type": "lead_captured"}])
        client = TestClient(app)
        res = client.post(f"/api/v1/automation-rules/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Auto Follow-up",
            "trigger_type": "lead_captured",
            "actions": [{"type": "send_email", "config": {"subject": "Hi", "body": "Hello"}}],
        })
        assert res.status_code == 200

    def test_create_rule_invalid_trigger(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/automation-rules/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Bad Trigger",
            "trigger_type": "invalid_trigger_xyz",
            "actions": [{"type": "send_email", "config": {}}],
        })
        assert res.status_code == 400

    def test_create_rule_invalid_action(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.post(f"/api/v1/automation-rules/{TEST_TENANT_ID}", headers=auth_headers, json={
            "name": "Bad Action",
            "trigger_type": "lead_captured",
            "actions": [{"type": "send_telegram_message", "config": {}}],
        })
        assert res.status_code == 400

    def test_list_rules(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("automation_rules", [], count=0)
        client = TestClient(app)
        res = client.get(f"/api/v1/automation-rules/{TEST_TENANT_ID}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "automation_rules" in data

    def test_tenant_logs_route_not_shadowed_by_rule_detail(self, mock_supabase, tenant_override, auth_headers):
        mock_supabase.set_table_data("automation_rule_executions", [], count=0)
        client = TestClient(app)
        res = client.get(f"/api/v1/automation-rules/{TEST_TENANT_ID}/logs", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data
        assert data["total"] == 0

    def test_list_trigger_types(self, mock_supabase, tenant_override, auth_headers):
        client = TestClient(app)
        res = client.get(f"/api/v1/automation-rules/{TEST_TENANT_ID}/triggers", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "triggers" in data
        assert len(data["triggers"]) > 10  # We have 15 trigger types

    def test_evaluate_trigger(self, mock_supabase, tenant_override, auth_headers):
        with patch("backend.services.automation_engine.evaluate_trigger", new_callable=AsyncMock) as mock_eval:
            mock_eval.return_value = (True, {"id": "lead-1"})
            client = TestClient(app)
            res = client.post(f"/api/v1/automation-rules/{TEST_TENANT_ID}/evaluate", headers=auth_headers, json={
                "trigger_type": "lead_captured",
                "trigger_config": {},
            })
            assert res.status_code == 200
            data = res.json()
            assert data["matches"] is True
