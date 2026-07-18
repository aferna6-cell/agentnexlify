"""Unit tests for GET /api/v1/analytics/{tenant_id}/attribution (GH #453).

Aggregates leads.attribution jsonb (migration 172: source, utm_source,
utm_medium, utm_campaign) into chartable breakdowns. Contract:

  1. Grouping: counts by source, medium, campaign, sorted desc.
  2. Leads with no attribution bucket under "(none)" so the tenant can see
     how much traffic is still unattributed.
  3. Tenant isolation: another tenant's token is rejected (leads is a
     client_id table — CLAUDE.md invariant #1).
"""

from unittest.mock import MagicMock

from backend.routers.analytics import insights as insights_module
from backend.tests.conftest import _make_auth_token

TENANT_ID = "00000000-0000-0000-0000-000000000001"
URL = f"/api/v1/analytics/{TENANT_ID}/attribution"
OTHER_TENANT = "00000000-0000-0000-0000-000000000002"


def _auth_headers(tenant_id=TENANT_ID):
    return {"Authorization": f"Bearer {_make_auth_token(tenant_id)}"}


def _wire_leads(mock_supabase, rows):
    result = MagicMock()
    result.data = rows
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = result
    mock_supabase.table.return_value = chain
    return chain


def _clear_cache():
    insights_module._cache.clear()


class TestAttributionBreakdown:
    def test_groups_by_source_medium_campaign(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(
            mock_supabase,
            [
                {"attribution": {"source": "google", "utm_medium": "cpc", "utm_campaign": "spring"}},
                {"attribution": {"source": "google", "utm_medium": "cpc", "utm_campaign": "spring"}},
                {"attribution": {"source": "facebook", "utm_medium": "social", "utm_campaign": "launch"}},
                {"attribution": {"source": "google", "utm_medium": "organic"}},
            ],
        )
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 4
        assert body["by_source"][0] == {"name": "google", "count": 3}
        assert {"name": "facebook", "count": 1} in body["by_source"]
        assert body["by_medium"][0] == {"name": "cpc", "count": 2}
        assert {"name": "spring", "count": 2} in body["by_campaign"]

    def test_unattributed_leads_bucket_as_none(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(
            mock_supabase,
            [
                {"attribution": None},
                {},
                {"attribution": {"source": "google"}},
            ],
        )
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert {"name": "(none)", "count": 2} in body["by_source"]
        # Medium/campaign missing on the google lead buckets as (none) too.
        assert {"name": "(none)", "count": 3} in body["by_medium"]
        assert body["attributed"] == 1

    def test_zero_leads_returns_empty_shape(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(mock_supabase, [])
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body == {
            "by_source": [],
            "by_medium": [],
            "by_campaign": [],
            "total": 0,
            "attributed": 0,
        }

    def test_other_tenants_token_is_rejected(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(mock_supabase, [{"attribution": {"source": "google"}}])
        resp = client.get(URL, headers=_auth_headers(OTHER_TENANT))
        assert resp.status_code in (401, 403)
