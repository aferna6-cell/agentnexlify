"""Warehouse free text stays 'other' until WAREHOUSE_LOGISTICS_ENABLED is on."""

import pytest

from backend.config import settings
from backend.services.business_type_storage import (
    apply_website_inferred_business_type,
    business_type_for_settings_write,
    business_type_for_website_inference_write,
    business_type_for_wizard_write,
)
from backend.services.industry_packs import load_pack


def _flag(monkeypatch, enabled: bool) -> None:
    monkeypatch.setattr(settings, "warehouse_logistics_enabled", enabled)


class _Update:
    def __init__(self, sink):
        self.sink = sink

    def update(self, data):
        self.sink["update"] = data
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Result", (), {"data": [self.sink.get("update")]})()


class _DB:
    def __init__(self, sink):
        self.sink = sink

    def table(self, _name):
        return _Update(self.sink)


@pytest.mark.parametrize("raw", ["freight", "logistics"])
@pytest.mark.parametrize(
    "write",
    [
        business_type_for_wizard_write,
        business_type_for_settings_write,
        business_type_for_website_inference_write,
    ],
)
def test_flag_off_saves_warehouse_free_text_as_other(monkeypatch, raw, write):
    _flag(monkeypatch, False)
    assert write(raw) == "other"


@pytest.mark.parametrize("raw", ["freight", "logistics"])
@pytest.mark.parametrize(
    "write",
    [
        business_type_for_wizard_write,
        business_type_for_settings_write,
        business_type_for_website_inference_write,
    ],
)
def test_flag_on_maps_warehouse_free_text(monkeypatch, raw, write):
    _flag(monkeypatch, True)
    assert write(raw) == "warehouse_logistics"


def test_website_inferred_update_uses_other_when_flag_off(monkeypatch):
    _flag(monkeypatch, False)
    sink = {}
    saved = apply_website_inferred_business_type(_DB(sink), "tenant-1", "freight")
    assert saved == "other"
    assert sink["update"] == {"business_type": "other"}


def test_website_inferred_update_maps_when_flag_on(monkeypatch):
    _flag(monkeypatch, True)
    sink = {}
    saved = apply_website_inferred_business_type(_DB(sink), "tenant-1", "logistics")
    assert saved == "warehouse_logistics"
    assert sink["update"]["business_type"] == "warehouse_logistics"


@pytest.mark.asyncio
async def test_settings_write_path_saves_other_when_flag_off(monkeypatch):
    _flag(monkeypatch, False)
    sink = {}
    monkeypatch.setattr(
        "backend.routers.auth.get_service_supabase", lambda: _DB(sink)
    )
    from backend.routers.auth import update_settings

    class _Request:
        async def json(self):
            return {"business_type": "logistics"}

    await update_settings("tenant-1", _Request(), {"tenant_id": "tenant-1"})
    assert sink["update"]["business_type"] == "other"


@pytest.mark.asyncio
async def test_settings_write_path_maps_when_flag_on(monkeypatch):
    _flag(monkeypatch, True)
    sink = {}
    monkeypatch.setattr(
        "backend.routers.auth.get_service_supabase", lambda: _DB(sink)
    )
    from backend.routers.auth import update_settings

    class _Request:
        async def json(self):
            return {"business_type": "freight"}

    await update_settings("tenant-1", _Request(), {"tenant_id": "tenant-1"})
    assert sink["update"]["business_type"] == "warehouse_logistics"


def test_pack_mapping_stays_default_until_flag_on(monkeypatch):
    _flag(monkeypatch, False)
    assert load_pack("freight").key == "default"
    assert load_pack("logistics").key == "default"
    _flag(monkeypatch, True)
    assert load_pack("freight").key == "warehouse_logistics"
    assert load_pack("logistics").key == "warehouse_logistics"
