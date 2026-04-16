"""Focused tests for Marketing Suite add-on gating."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.services import addon_gate


def _db_with_tenant_rows(rows):
    db = MagicMock()
    table = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=rows)
    db.table.return_value = table
    return db


def test_tenant_has_addon_reads_active_flag(monkeypatch):
    db = _db_with_tenant_rows([{"marketing_addon_active": True}])
    monkeypatch.setattr(addon_gate, "get_service_supabase", lambda: db)

    assert addon_gate._tenant_has_addon("tenant-1") is True
    db.table.assert_called_once_with("tenants")


def test_tenant_has_addon_blocks_missing_or_inactive(monkeypatch):
    db = _db_with_tenant_rows([{"marketing_addon_active": False}])
    monkeypatch.setattr(addon_gate, "get_service_supabase", lambda: db)
    assert addon_gate._tenant_has_addon("tenant-1") is False

    empty_db = _db_with_tenant_rows([])
    monkeypatch.setattr(addon_gate, "get_service_supabase", lambda: empty_db)
    assert addon_gate._tenant_has_addon("tenant-1") is False


@pytest.mark.asyncio
async def test_require_marketing_addon_allows_active_tenant(monkeypatch):
    claims = {"tenant_id": "tenant-1", "role": "owner"}
    monkeypatch.setattr(addon_gate, "_tenant_has_addon", lambda tenant_id: True)

    assert await addon_gate.require_marketing_addon(claims) == claims


@pytest.mark.asyncio
async def test_require_marketing_addon_returns_payment_required(monkeypatch):
    claims = {"tenant_id": "tenant-1", "role": "owner"}
    monkeypatch.setattr(addon_gate, "_tenant_has_addon", lambda tenant_id: False)

    with pytest.raises(HTTPException) as exc_info:
        await addon_gate.require_marketing_addon(claims)

    exc = exc_info.value
    assert exc.status_code == 402
    assert exc.detail["error"] == "marketing_addon_required"
    assert exc.detail["upgrade_path"] == addon_gate.MARKETING_ADDON_UPGRADE_PATH
