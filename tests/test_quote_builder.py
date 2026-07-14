"""Instant quoting (#R2) — unit tests.

Contracts:
  - build_quote grounds on the tenant's own service_types catalog and inserts
    a quotes row (status 'draft').
  - the "never invent prices" guarantee is HARD when a catalog exists:
    _sanitize_tier drops any line item whose price isn't an exact catalog match.
  - build_quote never raises: empty job_description, service_types lookup
    failure, LLM failure, and unparseable output all return None.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import backend.services.quote_builder as quote_builder
from backend.services.quote_builder import _sanitize_tier, build_quote

TENANT = "22222222-2222-2222-2222-222222222222"


def _llm(text):
    r = MagicMock()
    r.text = text
    return r


def _tenants_db(business_name="Acme Plumbing", business_type="plumber"):
    db = MagicMock()
    chain = MagicMock()
    for m in ["select", "eq"]:
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(
        data=[{"business_name": business_name, "business_type": business_type}]
    )
    db.table.return_value = chain
    return db


def _tenant_table_factory(services, inserted_row):
    """Return a fake tenant_table(db, name, tenant_id) dispatching by table name."""
    def _factory(_db, name, _tenant_id):
        chain = MagicMock()
        if name == "service_types":
            for m in ["select", "eq"]:
                getattr(chain, m).return_value = chain
            chain.execute.return_value = MagicMock(data=services)
        else:  # quotes insert
            chain.insert.return_value = chain
            chain.execute.return_value = MagicMock(data=[inserted_row])
        return chain
    return _factory


# ---------------------------------------------------------------------------
# _sanitize_tier — the hard "never invent prices" guarantee
# ---------------------------------------------------------------------------


def test_sanitize_tier_drops_out_of_catalog_prices_when_catalog_present():
    raw = {"line_items": [
        {"name": "Drain clean", "description": "d", "price": 150.0},   # in catalog
        {"name": "Invented", "description": "d", "price": 999.0},      # NOT in catalog
    ]}
    tier = _sanitize_tier(raw, allowed_prices={150.0}, has_catalog=True)
    assert [i["name"] for i in tier["line_items"]] == ["Drain clean"]
    assert tier["total"] == 150.0


# ---------------------------------------------------------------------------
# build_quote
# ---------------------------------------------------------------------------


def test_build_quote_grounds_on_catalog_and_inserts_row():
    services = [
        {"name": "Drain cleaning", "description": "clear a drain", "price": 150.0},
        {"name": "Water heater install", "description": "install", "price": 1200.0},
    ]
    llm = (
        '{"good": {"line_items": [{"name": "Drain cleaning", "description": "clear", "price": 150.0}]},'
        ' "better": {"line_items": [{"name": "Water heater install", "description": "x", "price": 1200.0}]},'
        ' "best": {"line_items": [{"name": "Bogus upsell", "description": "x", "price": 5000.0}]}}'
    )
    inserted = {"id": "q1", "tenant_id": TENANT, "status": "draft"}
    with patch.object(quote_builder, "get_service_supabase", return_value=_tenants_db()), patch.object(
        quote_builder, "tenant_table", new=_tenant_table_factory(services, inserted)
    ), patch.object(
        quote_builder, "call_claude_messages", new=AsyncMock(return_value=_llm(llm))
    ) as call:
        result = asyncio.run(
            build_quote(tenant_id=TENANT, job_description="my drain is clogged")
        )

    assert result == inserted
    assert call.await_args.kwargs["model"] == "claude-sonnet-5"
    # (Catalog-price grounding of the stored tiers is asserted directly in
    # test_build_quote_drops_invented_price_in_stored_tiers below.)


def test_build_quote_drops_invented_price_in_stored_tiers():
    services = [{"name": "Drain cleaning", "description": "d", "price": 150.0}]
    llm = (
        '{"good": {"line_items": [{"name": "Drain cleaning", "description": "c", "price": 150.0}]},'
        ' "better": {"line_items": [{"name": "Invented", "description": "c", "price": 999.0}]},'
        ' "best": {"line_items": []}}'
    )
    captured = {}

    def _factory(_db, name, _tenant_id):
        chain = MagicMock()
        if name == "service_types":
            for m in ["select", "eq"]:
                getattr(chain, m).return_value = chain
            chain.execute.return_value = MagicMock(data=services)
        else:
            def _insert(row):
                captured["row"] = row
                inner = MagicMock()
                inner.execute.return_value = MagicMock(data=[{"id": "q2", **row}])
                return inner
            chain.insert.side_effect = _insert
        return chain

    with patch.object(quote_builder, "get_service_supabase", return_value=_tenants_db()), patch.object(
        quote_builder, "tenant_table", new=_factory
    ), patch.object(
        quote_builder, "call_claude_messages", new=AsyncMock(return_value=_llm(llm))
    ):
        result = asyncio.run(build_quote(tenant_id=TENANT, job_description="clogged drain"))

    assert result is not None
    tiers = captured["row"]["tiers"]
    assert [i["name"] for i in tiers["good"]["line_items"]] == ["Drain cleaning"]
    # invented $999 line dropped -> "better" tier has no line items
    assert tiers["better"]["line_items"] == []


def test_build_quote_empty_job_description_returns_none():
    result = asyncio.run(build_quote(tenant_id=TENANT, job_description="   "))
    assert result is None


def test_build_quote_llm_failure_returns_none():
    services = [{"name": "X", "description": "d", "price": 10.0}]
    inserted = {"id": "q", "tenant_id": TENANT}
    with patch.object(quote_builder, "get_service_supabase", return_value=_tenants_db()), patch.object(
        quote_builder, "tenant_table", new=_tenant_table_factory(services, inserted)
    ), patch.object(
        quote_builder, "call_claude_messages", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        result = asyncio.run(build_quote(tenant_id=TENANT, job_description="job"))
    assert result is None


def test_build_quote_unparseable_returns_none():
    services = [{"name": "X", "description": "d", "price": 10.0}]
    inserted = {"id": "q", "tenant_id": TENANT}
    with patch.object(quote_builder, "get_service_supabase", return_value=_tenants_db()), patch.object(
        quote_builder, "tenant_table", new=_tenant_table_factory(services, inserted)
    ), patch.object(
        quote_builder, "call_claude_messages", new=AsyncMock(return_value=_llm("not json"))
    ):
        result = asyncio.run(build_quote(tenant_id=TENANT, job_description="job"))
    assert result is None
