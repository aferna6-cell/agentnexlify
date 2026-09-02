"""Tests for the marketing plan gate (replaced the retired $49.99 add-on gate
2026-06-10 — marketing features are now included with Growth/autopilot+ and
surfaced via Agent OS)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.services import plan_gate


def _db_with_tenant_rows(rows):
    db = MagicMock()
    table = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=rows)
    db.table.return_value = table
    return db


def test_tenant_plan_reads_plan(monkeypatch):
    db = _db_with_tenant_rows([{"plan": "autopilot"}])
    monkeypatch.setattr(plan_gate, "get_service_supabase", lambda: db)
    assert plan_gate._tenant_plan("tenant-1") == "autopilot"
    db.table.assert_called_once_with("tenants")


@pytest.mark.parametrize("plan", sorted(plan_gate.MARKETING_PLANS))
@pytest.mark.asyncio
async def test_marketing_plans_pass(monkeypatch, plan):
    db = _db_with_tenant_rows([{"plan": plan}])
    monkeypatch.setattr(plan_gate, "get_service_supabase", lambda: db)
    claims = {"tenant_id": "tenant-1"}
    assert await plan_gate.require_marketing_access(claims) is claims


@pytest.mark.parametrize("plan", ["free", "chatbot", "", None])
@pytest.mark.asyncio
async def test_non_marketing_plans_blocked_with_402(monkeypatch, plan):
    db = _db_with_tenant_rows([{"plan": plan}])
    monkeypatch.setattr(plan_gate, "get_service_supabase", lambda: db)
    with pytest.raises(HTTPException) as exc_info:
        await plan_gate.require_marketing_access({"tenant_id": "tenant-1"})
    assert exc_info.value.status_code == 402
    detail = exc_info.value.detail
    assert detail["error"] == "plan_upgrade_required"
    assert detail["upgrade_path"] == "/billing"


@pytest.mark.asyncio
async def test_missing_tenant_claims_401():
    with pytest.raises(HTTPException) as exc_info:
        await plan_gate.require_marketing_access({})
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_unknown_tenant_blocked(monkeypatch):
    db = _db_with_tenant_rows([])
    monkeypatch.setattr(plan_gate, "get_service_supabase", lambda: db)
    with pytest.raises(HTTPException) as exc_info:
        await plan_gate.require_marketing_access({"tenant_id": "ghost"})
    assert exc_info.value.status_code == 402
