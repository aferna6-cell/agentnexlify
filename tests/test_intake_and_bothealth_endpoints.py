"""Endpoint + loop coverage for the #R1/#R2/#R4 routers.

Exercises the router layer (auth, widget-key resolution, success + failure
responses) and bot_health.score_all_tenants, which the service-level tests
don't reach.
"""

import os

os.environ["TESTING"] = "1"

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.services.bot_health as bot_health
from backend.main import app

client = TestClient(app)

_JWT_SECRET = "test-secret-key-for-jwt"
TENANT = "00000000-0000-0000-0000-000000000001"


def _token(tenant_id=TENANT):
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "owner@example.com",
        "role": "owner",
        "plan": "agent_os",
        "business_name": "Test Biz",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _auth(tenant_id=TENANT):
    return {"Authorization": f"Bearer {_token(tenant_id)}"}


# ---------------------------------------------------------------------------
# intake_ai — POST /api/v1/photo-triage (widget-key auth)
# ---------------------------------------------------------------------------

_IMG_BODY = {
    "api_key": "anx_test",
    "images": [{"media_type": "image/jpeg", "data": "ZmFrZQ=="}],
    "note": "leaking",
}


def test_photo_triage_endpoint_returns_assessment():
    triage = {
        "urgency": "high",
        "category": "burst pipe",
        "scope_summary": "leak",
        "recommended_action": "book now",
    }
    with patch("backend.routers.intake_ai._get_widget_config", return_value={"tenant_id": TENANT}), \
         patch("backend.routers.intake_ai._get_tenant", return_value={"business_type": "plumber"}), \
         patch("backend.routers.intake_ai.triage_photos", new=AsyncMock(return_value=triage)):
        resp = client.post("/api/v1/photo-triage", json=_IMG_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["urgency"] == "high"


def test_photo_triage_endpoint_unavailable_when_triage_none():
    with patch("backend.routers.intake_ai._get_widget_config", return_value={"tenant_id": TENANT}), \
         patch("backend.routers.intake_ai._get_tenant", return_value={"business_type": "plumber"}), \
         patch("backend.routers.intake_ai.triage_photos", new=AsyncMock(return_value=None)):
        resp = client.post("/api/v1/photo-triage", json=_IMG_BODY)
    assert resp.status_code == 200
    assert resp.json()["status"] == "unavailable"


def test_photo_triage_endpoint_bad_widget_key_raises():
    with patch(
        "backend.routers.intake_ai._get_widget_config",
        side_effect=HTTPException(status_code=404, detail="Invalid API key"),
    ):
        resp = client.post("/api/v1/photo-triage", json=_IMG_BODY)
    assert resp.status_code == 404


def test_photo_triage_endpoint_survives_tenant_lookup_failure():
    triage = {"urgency": "low", "category": "c", "scope_summary": "s", "recommended_action": "a"}
    with patch("backend.routers.intake_ai._get_widget_config", return_value={"tenant_id": TENANT}), \
         patch("backend.routers.intake_ai._get_tenant", side_effect=RuntimeError("db down")), \
         patch("backend.routers.intake_ai.triage_photos", new=AsyncMock(return_value=triage)):
        resp = client.post("/api/v1/photo-triage", json=_IMG_BODY)
    assert resp.status_code == 200
    assert resp.json()["urgency"] == "low"


# ---------------------------------------------------------------------------
# intake_ai — POST /api/v1/quotes/build (JWT)
# ---------------------------------------------------------------------------


def test_quote_build_endpoint_returns_row():
    row = {
        "id": "q1", "tenant_id": TENANT, "lead_id": None,
        "job_description": "clogged drain", "triage": None,
        "tiers": {"good": {"line_items": [], "total": 0.0, "note": None}},
        "status": "draft", "created_at": "2026-07-14T00:00:00+00:00",
        "updated_at": "2026-07-14T00:00:00+00:00",
    }
    with patch("backend.routers.intake_ai.build_quote", new=AsyncMock(return_value=row)):
        resp = client.post(
            "/api/v1/quotes/build", json={"job_description": "clogged drain"}, headers=_auth()
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == "q1"


def test_quote_build_endpoint_requires_auth():
    # No Authorization header -> the _get_current_tenant dependency rejects it
    # (422 = required auth header missing; 401/403 if a token is malformed).
    resp = client.post("/api/v1/quotes/build", json={"job_description": "x"})
    assert resp.status_code in (401, 403, 422)


def test_quote_build_endpoint_502_when_builder_returns_none():
    with patch("backend.routers.intake_ai.build_quote", new=AsyncMock(return_value=None)):
        resp = client.post(
            "/api/v1/quotes/build", json={"job_description": "x"}, headers=_auth()
        )
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# bot_health router — GET /{tenant_id}, POST /run
# ---------------------------------------------------------------------------


def _score_row():
    return {
        "id": "s1", "tenant_id": TENANT, "computed_at": "2026-07-14T00:00:00+00:00",
        "window_days": 7, "sample_size": 5, "resolution_rate": 0.8,
        "hallucination_flag_count": 0, "unresolved_intent_count": 1,
        "avg_sentiment": 0.5, "health_score": 82.0, "details": {},
    }


def test_bot_health_get_returns_latest_row():
    chain = MagicMock()
    for m in ["select", "order", "limit"]:
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[_score_row()])
    with patch("backend.routers.bot_health.get_service_supabase", return_value=MagicMock()), \
         patch("backend.routers.bot_health.tenant_table", return_value=chain):
        resp = client.get(f"/api/v1/bot-health/{TENANT}", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["health_score"] == 82.0


def test_bot_health_get_rejects_other_tenant():
    resp = client.get("/api/v1/bot-health/99999999-9999-9999-9999-999999999999", headers=_auth())
    assert resp.status_code == 403


def test_bot_health_run_scores_with_admin_secret():
    with patch("backend.routers.bot_health._admin_secret", return_value="sekret"), \
         patch("backend.routers.bot_health.score_all_tenants", new=AsyncMock(return_value={"scored": 2, "skipped": 1})):
        resp = client.post("/api/v1/bot-health/run", headers={"X-Api-Secret": "sekret"})
    assert resp.status_code == 200
    assert resp.json() == {"scored": 2, "skipped": 1}


def test_bot_health_run_rejects_bad_secret():
    with patch("backend.routers.bot_health._admin_secret", return_value="sekret"):
        resp = client.post("/api/v1/bot-health/run", headers={"X-Api-Secret": "wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# bot_health.score_all_tenants — the cron loop
# ---------------------------------------------------------------------------


def test_score_all_tenants_counts_scored_and_skipped():
    import asyncio

    db = MagicMock()
    tenants_chain = MagicMock()
    tenants_chain.select.return_value = tenants_chain
    # score_all_tenants reads row["id"] from tenants.select("id")
    tenants_chain.execute.return_value = MagicMock(data=[{"id": "t1"}, {"id": "t2"}])
    db.table.return_value = tenants_chain

    async def _fake_score(tenant_id, window_days=7):
        return {"id": "x"} if tenant_id == "t1" else None

    with patch.object(bot_health, "get_service_supabase", return_value=db), \
         patch.object(bot_health, "score_tenant_bot_health", new=AsyncMock(side_effect=_fake_score)):
        result = asyncio.run(bot_health.score_all_tenants())
    assert result["scored"] == 1
    assert result["skipped"] == 1
