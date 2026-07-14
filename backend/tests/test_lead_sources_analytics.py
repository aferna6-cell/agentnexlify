"""Unit tests for GET /api/v1/analytics/{tenant_id}/lead-sources (GH #409).

The endpoint shipped in backend/routers/analytics/insights.py:181; the issue's
acceptance criteria ask for unit coverage of grouping, null-source bucketing,
and client_id scoping (leads is a client_id table — CLAUDE.md invariant #1).
"""

from unittest.mock import MagicMock

from backend.routers.analytics import insights as insights_module
from backend.tests.conftest import _make_auth_token

TENANT_ID = "00000000-0000-0000-0000-000000000001"
URL = f"/api/v1/analytics/{TENANT_ID}/lead-sources"
OTHER_TENANT = "00000000-0000-0000-0000-000000000002"


def _auth_headers(tenant_id=TENANT_ID):
    return {"Authorization": f"Bearer {_make_auth_token(tenant_id)}"}


def _wire_leads(mock_supabase, rows):
    result = MagicMock()
    result.data = rows
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = result
    mock_supabase.table.return_value = chain
    return chain


def _clear_cache():
    insights_module._cache.clear()


class TestLeadSourceBreakdown:
    def test_groups_and_sorts_by_count(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(
            mock_supabase,
            [
                {"source": "widget"},
                {"source": "widget"},
                {"source": "manual"},
                {"source": "widget"},
                {"source": "booking"},
                {"source": "manual"},
            ],
        )
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 6
        assert body["breakdown"][0] == {"source": "widget", "count": 3}
        assert {"source": "manual", "count": 2} in body["breakdown"]
        assert {"source": "booking", "count": 1} in body["breakdown"]

    def test_null_source_buckets_as_widget(self, client, mock_supabase):
        """Sourceless rows bucket under 'widget' — the widget is the only
        capture path that historically wrote no source value."""
        _clear_cache()
        _wire_leads(mock_supabase, [{"source": None}, {}, {"source": "manual"}])
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert {"source": "widget", "count": 2} in body["breakdown"]
        assert body["total"] == 3

    def test_zero_leads_returns_empty_breakdown(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(mock_supabase, [])
        resp = client.get(URL, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"breakdown": [], "total": 0}

    def test_scopes_to_client_id(self, client, mock_supabase):
        _clear_cache()
        chain = _wire_leads(mock_supabase, [])
        client.get(URL, headers=_auth_headers())
        chain.eq.assert_called_with("client_id", TENANT_ID)

    def test_cross_tenant_access_forbidden(self, client, mock_supabase):
        _clear_cache()
        _wire_leads(mock_supabase, [])
        resp = client.get(URL, headers=_auth_headers(OTHER_TENANT))
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.get(URL)
        assert resp.status_code in (401, 422)
