"""Unit tests for backend.services.pipeline_presets.

Covers preset resolution (DEFAULT_STAGES fallback, alias mapping, direct match)
and seed_default_stages (tenant lookup success, failure, no business_type,
insert failure path).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock


from backend.services.pipeline_presets import (
    DEFAULT_STAGES,
    _INDUSTRY_STAGES,
    _TYPE_ALIASES,
    resolve_stages_for_business_type,
    seed_default_stages,
)


class TestResolveStagesForBusinessType:
    def test_none_returns_default(self):
        assert resolve_stages_for_business_type(None) == DEFAULT_STAGES

    def test_empty_returns_default(self):
        assert resolve_stages_for_business_type("") == DEFAULT_STAGES

    def test_unknown_returns_default(self):
        assert resolve_stages_for_business_type("not-an-industry") == DEFAULT_STAGES

    def test_direct_industry_match(self):
        result = resolve_stages_for_business_type("realestate")
        assert result == _INDUSTRY_STAGES["realestate"]
        assert any(s["name"] == "Showing Scheduled" for s in result)

    def test_alias_real_estate_maps_to_realestate(self):
        result = resolve_stages_for_business_type("real_estate")
        assert result == _INDUSTRY_STAGES["realestate"]

    def test_alias_plumbing_maps_to_contractor(self):
        result = resolve_stages_for_business_type("plumbing")
        assert result == _INDUSTRY_STAGES["contractor"]
        assert any(s["name"] == "Estimate Sent" for s in result)

    def test_alias_beauty_maps_to_salon(self):
        result = resolve_stages_for_business_type("beauty")
        assert result == _INDUSTRY_STAGES["salon"]

    def test_alias_medical_maps_to_dental(self):
        result = resolve_stages_for_business_type("medical")
        assert result == _INDUSTRY_STAGES["dental"]

    def test_case_insensitive(self):
        assert resolve_stages_for_business_type("REALESTATE") == _INDUSTRY_STAGES["realestate"]
        assert resolve_stages_for_business_type("Plumbing") == _INDUSTRY_STAGES["contractor"]

    def test_all_aliases_resolve(self):
        for alias, target in _TYPE_ALIASES.items():
            result = resolve_stages_for_business_type(alias)
            assert result == _INDUSTRY_STAGES[target], f"alias {alias} broken"


def _fake_db_with_business_type(business_type, insert_returns=None, insert_raises=False, tenant_raises=False):
    """Build a mock db client whose table().select().eq().limit().execute() returns the given business_type."""
    db = MagicMock()

    tenant_table = MagicMock()
    select_q = MagicMock()
    eq_q = MagicMock()
    limit_q = MagicMock()
    if tenant_raises:
        limit_q.execute.side_effect = RuntimeError("tenant lookup boom")
    else:
        limit_q.execute.return_value = SimpleNamespace(
            data=[{"business_type": business_type}] if business_type is not None else []
        )
    limit_q.limit = MagicMock(return_value=limit_q)
    eq_q.limit = MagicMock(return_value=limit_q)
    select_q.eq = MagicMock(return_value=eq_q)
    tenant_table.select = MagicMock(return_value=select_q)

    insert_table = MagicMock()
    insert_q = MagicMock()
    if insert_raises:
        insert_q.execute.side_effect = RuntimeError("insert boom")
    else:
        insert_q.execute.return_value = SimpleNamespace(data=insert_returns or [])
    insert_table.insert = MagicMock(return_value=insert_q)

    def _table(name):
        return tenant_table if name == "tenants" else insert_table

    db.table = MagicMock(side_effect=_table)
    return db, insert_table


class TestSeedDefaultStages:
    def test_uses_industry_preset_when_business_type_set(self):
        db, insert_table = _fake_db_with_business_type(
            "realestate",
            insert_returns=[{"id": "stage-1"}],
        )

        result = seed_default_stages("tenant-abc", db)

        assert result == [{"id": "stage-1"}]
        insert_args = insert_table.insert.call_args.args[0]
        assert len(insert_args) == len(_INDUSTRY_STAGES["realestate"])
        assert all(row["tenant_id"] == "tenant-abc" for row in insert_args)
        assert insert_args[0]["name"] == "New Lead"

    def test_uses_alias_when_business_type_is_alias(self):
        db, insert_table = _fake_db_with_business_type("plumbing", insert_returns=[])
        seed_default_stages("tenant-xyz", db)
        names = [row["name"] for row in insert_table.insert.call_args.args[0]]
        assert "Estimate Sent" in names

    def test_falls_back_to_default_when_no_tenant_row(self):
        db, insert_table = _fake_db_with_business_type(None, insert_returns=[])
        seed_default_stages("tenant-none", db)
        rows = insert_table.insert.call_args.args[0]
        assert len(rows) == len(DEFAULT_STAGES)
        assert rows[0]["name"] == DEFAULT_STAGES[0]["name"]

    def test_falls_back_to_default_when_tenant_lookup_raises(self):
        db, insert_table = _fake_db_with_business_type(
            None, insert_returns=[{"id": "stage-1"}], tenant_raises=True
        )
        result = seed_default_stages("tenant-err", db)
        assert result == [{"id": "stage-1"}]
        rows = insert_table.insert.call_args.args[0]
        assert len(rows) == len(DEFAULT_STAGES)

    def test_returns_empty_list_when_insert_raises(self):
        db, _ = _fake_db_with_business_type("realestate", insert_raises=True)
        result = seed_default_stages("tenant-fail", db)
        assert result == []

    def test_returns_empty_list_when_insert_returns_none(self):
        db, insert_table = _fake_db_with_business_type("realestate", insert_returns=None)
        insert_table.insert.return_value.execute.return_value = SimpleNamespace(data=None)
        result = seed_default_stages("tenant-null", db)
        assert result == []
