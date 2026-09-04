"""Endpoint-level tests for the insights + appointment-brief + ai-usage
routers (2026-08-06 additions): auth boundaries, happy paths, error mapping.
"""

import os
from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import appointment_briefs as briefs_mod
from backend.routers import billing_usage as billing_mod
from backend.routers import insights as insights_mod
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.appointment_brief import AppointmentBriefError
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase import db

TENANT = "22222222-2222-2222-2222-222222222222"
CLAIMS = {"tenant_id": TENANT}


def _client(claims=CLAIMS):
    app.dependency_overrides[_get_current_tenant] = lambda: claims
    # Brief endpoints now carry the Agent OS plan gate; these tests cover
    # auth/error mapping, not plan gating (see test_appointment_briefs_gating).
    app.dependency_overrides[require_agent_os_access] = lambda: claims
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


# --- /api/v1/insights ------------------------------------------------------


def test_daily_focus_returns_picks():
    client = _client()
    try:
        with patch.object(insights_mod, "get_service_supabase", return_value=db({})), \
             patch.object(insights_mod, "compute_daily_focus", return_value=[{"kind": "new_leads"}]):
            resp = client.get(f"/api/v1/insights/{TENANT}/daily-focus")
        assert resp.status_code == 200
        assert resp.json() == {"picks": [{"kind": "new_leads"}]}
    finally:
        _teardown()


def test_daily_focus_rejects_foreign_tenant():
    client = _client()
    try:
        resp = client.get("/api/v1/insights/other-tenant/daily-focus")
        assert resp.status_code == 403
    finally:
        _teardown()


def test_response_score_returns_snapshot():
    client = _client()
    try:
        with patch.object(insights_mod, "get_service_supabase", return_value=db({})), \
             patch.object(insights_mod, "compute_response_score", return_value={"score": 88.0, "grade": "B"}):
            resp = client.get(f"/api/v1/insights/{TENANT}/response-score")
        assert resp.status_code == 200
        assert resp.json()["grade"] == "B"
    finally:
        _teardown()


# --- /api/v1/appointments/{t}/{a}/brief + follow-up-draft ------------------


def test_brief_happy_path():
    async def fake_brief(db_, tenant_id, appointment_id, business_name=""):
        return {"brief": "## Who they are\nCara.", "has_history": True}

    client = _client()
    try:
        with patch.object(briefs_mod, "get_service_supabase", return_value=db({})), \
             patch.object(briefs_mod.appointment_brief, "generate_brief", fake_brief):
            resp = client.post(f"/api/v1/appointments/{TENANT}/a1/brief")
        assert resp.status_code == 200
        assert resp.json()["has_history"] is True
    finally:
        _teardown()


def test_brief_missing_appointment_404():
    async def missing(db_, tenant_id, appointment_id, business_name=""):
        raise AppointmentBriefError("Appointment not found")

    client = _client()
    try:
        with patch.object(briefs_mod, "get_service_supabase", return_value=db({})), \
             patch.object(briefs_mod.appointment_brief, "generate_brief", missing):
            resp = client.post(f"/api/v1/appointments/{TENANT}/missing/brief")
        assert resp.status_code == 404
    finally:
        _teardown()


def test_brief_llm_failure_maps_to_502():
    async def boom(db_, tenant_id, appointment_id, business_name=""):
        raise RuntimeError("claude down")

    client = _client()
    try:
        with patch.object(briefs_mod, "get_service_supabase", return_value=db({})), \
             patch.object(briefs_mod.appointment_brief, "generate_brief", boom):
            resp = client.post(f"/api/v1/appointments/{TENANT}/a1/brief")
        assert resp.status_code == 502
    finally:
        _teardown()


def test_brief_rejects_foreign_tenant():
    client = _client()
    try:
        resp = client.post("/api/v1/appointments/other-tenant/a1/brief")
        assert resp.status_code == 403
    finally:
        _teardown()


def test_followup_draft_happy_path():
    async def fake_draft(db_, tenant_id, appointment_id, business_name=""):
        return {"subject": "Great seeing you", "body": "Thanks!", "customer_email": "c@x.com"}

    client = _client()
    try:
        with patch.object(briefs_mod, "get_service_supabase", return_value=db({})), \
             patch.object(briefs_mod.appointment_brief, "draft_followup", fake_draft):
            resp = client.post(f"/api/v1/appointments/{TENANT}/a1/follow-up-draft")
        assert resp.status_code == 200
        assert resp.json()["subject"] == "Great seeing you"
    finally:
        _teardown()


def test_followup_draft_error_maps_to_404_and_502():
    async def missing(db_, tenant_id, appointment_id, business_name=""):
        raise AppointmentBriefError("Appointment not found")

    async def boom(db_, tenant_id, appointment_id, business_name=""):
        raise RuntimeError("claude down")

    client = _client()
    try:
        with patch.object(briefs_mod, "get_service_supabase", return_value=db({})):
            with patch.object(briefs_mod.appointment_brief, "draft_followup", missing):
                assert client.post(f"/api/v1/appointments/{TENANT}/a1/follow-up-draft").status_code == 404
            with patch.object(briefs_mod.appointment_brief, "draft_followup", boom):
                assert client.post(f"/api/v1/appointments/{TENANT}/a1/follow-up-draft").status_code == 502
    finally:
        _teardown()


def test_business_name_lookup_degrades_to_empty():
    class ExplodingDb:
        def table(self, name):
            raise RuntimeError("boom")

    assert briefs_mod._business_name(ExplodingDb(), TENANT) == ""
    fixture = db({"tenants": [{"business_name": "Acme"}]})
    assert briefs_mod._business_name(fixture, TENANT) == "Acme"


# --- /api/v1/billing/ai-usage ----------------------------------------------


def test_ai_usage_available_without_plan_gate():
    snapshot = {"limit_units": 100, "used_units": 40, "remaining_units": 60, "pct_used": 40.0}
    client = _client()
    try:
        with patch.object(billing_mod, "get_service_supabase", return_value=db({})), \
             patch.object(billing_mod, "get_ai_usage_status", return_value=snapshot):
            resp = client.get("/api/v1/billing/ai-usage")
        assert resp.status_code == 200
        assert resp.json() == {"ai_usage": snapshot}
    finally:
        _teardown()


def test_ai_usage_unauthenticated_401():
    client = _client(claims={})
    try:
        resp = client.get("/api/v1/billing/ai-usage")
        assert resp.status_code == 401
    finally:
        _teardown()
