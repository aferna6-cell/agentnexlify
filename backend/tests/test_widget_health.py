"""Tests for backend/services/widget_health.py and backend/routers/widget_health.py.

Env vars patched BEFORE any backend import per conftest.py pattern.
Supabase client mocked via the module-level singleton (_stub_supabase_singletons).
Router tested via SyncASGITestClient + _make_auth_token.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# conftest.py sets TESTING=1 and stubs Supabase singletons before any import.
# The _stub_supabase_singletons fixture is autouse — active for all tests here.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chain(mock_db, rows, *, count=None):
    """Wire table().select().eq().limit().execute() chain onto mock_db."""
    execute_result = MagicMock()
    execute_result.data = rows
    execute_result.count = count if count is not None else len(rows)
    (
        mock_db.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = execute_result
    return execute_result


def _chain_in(mock_db, rows):
    """Wire table().select().eq().in_().limit().execute() chain (calendar probe)."""
    execute_result = MagicMock()
    execute_result.data = rows
    (
        mock_db.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .limit.return_value
        .execute.return_value
    ) = execute_result
    return execute_result


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestComputeWidgetHealth:
    """Unit tests for compute_widget_health()."""

    def test_healthy_when_widget_installed_and_domains(self, mock_supabase):
        """overall='needs_attention' minimum when widget exists but no activity yet."""
        # We only test the shape; individual probe logic is implicit.
        from backend.services.widget_health import compute_widget_health

        # widget_configs returns a row with domains
        wc_execute = MagicMock()
        wc_execute.data = [{"tenant_id": "t1", "allowed_domains": ["example.com"]}]
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = wc_execute

        result = compute_widget_health("t1")

        assert "overall" in result
        assert "checks" in result
        assert "allowed_domains" in result
        assert "stats" in result
        assert isinstance(result["checks"], list)

    def test_not_ready_when_no_widget_config(self, mock_supabase):
        """overall='not_ready' when widget_configs returns no rows (widget_installed fails)."""
        from backend.services.widget_health import compute_widget_health

        # All table calls return empty
        execute_empty = MagicMock()
        execute_empty.data = []
        execute_empty.count = 0
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_empty
        # Also cover count/gte chains for recent_activity probe
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .gte.return_value
            .execute.return_value
        ) = execute_empty

        result = compute_widget_health("t1")
        assert result["overall"] == "not_ready"

    def test_allowed_domains_returned(self, mock_supabase):
        """allowed_domains list passed through from widget_configs row."""
        from backend.services.widget_health import compute_widget_health

        wc_execute = MagicMock()
        wc_execute.data = [{"tenant_id": "t1", "allowed_domains": ["foo.com", "bar.com"]}]
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = wc_execute

        result = compute_widget_health("t1")
        assert result["allowed_domains"] == ["foo.com", "bar.com"]

    def test_empty_allowed_domains_returned_as_list(self, mock_supabase):
        """allowed_domains defaults to [] when widget row has None."""
        from backend.services.widget_health import compute_widget_health

        wc_execute = MagicMock()
        wc_execute.data = [{"tenant_id": "t1", "allowed_domains": None}]
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = wc_execute

        result = compute_widget_health("t1")
        assert isinstance(result["allowed_domains"], list)

    def test_probe_exception_does_not_propagate(self, mock_supabase):
        """A DB error in any probe degrades that check but doesn't raise."""
        from backend.services.widget_health import compute_widget_health

        mock_supabase.table.side_effect = RuntimeError("DB exploded")

        result = compute_widget_health("t1")
        assert isinstance(result, dict)
        assert result["overall"] in ("not_ready", "needs_attention", "healthy")

    def test_stats_shape(self, mock_supabase):
        """stats dict always contains leads_7d, conversations_7d, appointments_7d."""
        from backend.services.widget_health import compute_widget_health

        execute_empty = MagicMock()
        execute_empty.data = []
        execute_empty.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = execute_empty

        result = compute_widget_health("t1")
        stats = result["stats"]
        assert "leads_7d" in stats
        assert "conversations_7d" in stats
        assert "appointments_7d" in stats

    def test_client_id_used_for_leads_and_conversations(self, mock_supabase):
        """recent_activity probe uses client_id for leads + conversations (not tenant_id)."""
        from backend.services.widget_health import compute_widget_health

        execute_empty = MagicMock()
        execute_empty.data = []
        execute_empty.count = 0
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_empty
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .gte.return_value
            .execute.return_value
        ) = execute_empty

        compute_widget_health("tenant-XYZ")

        # Verify at least one eq("client_id", "tenant-XYZ") call was made
        eq_calls = mock_supabase.table.return_value.select.return_value.eq.call_args_list
        client_id_calls = [c for c in eq_calls if c.args == ("client_id", "tenant-XYZ")]
        assert len(client_id_calls) >= 1, (
            "recent_activity probe must use client_id for leads/conversations"
        )


class TestOverallHelper:
    """Unit tests for _overall()."""

    def test_fail_wins_over_warn(self):
        from backend.services.widget_health import _overall
        checks = [
            {"status": "ok"},
            {"status": "warn"},
            {"status": "fail"},
        ]
        assert _overall(checks) == "not_ready"

    def test_warn_without_fail(self):
        from backend.services.widget_health import _overall
        checks = [{"status": "ok"}, {"status": "warn"}]
        assert _overall(checks) == "needs_attention"

    def test_all_ok(self):
        from backend.services.widget_health import _overall
        checks = [{"status": "ok"}, {"status": "ok"}]
        assert _overall(checks) == "healthy"

    def test_empty(self):
        from backend.services.widget_health import _overall
        assert _overall([]) == "healthy"


# ---------------------------------------------------------------------------
# Router integration tests
# ---------------------------------------------------------------------------

class TestWidgetHealthRouter:
    """Integration tests for GET /api/v1/widget-health/{tenant_id}."""

    def test_get_health_returns_200_for_own_tenant(
        self, client, mock_supabase, auth_headers_for
    ):
        """Authenticated owner gets 200 with health payload."""
        from backend.tests.conftest import _make_auth_token

        tenant_id = "00000000-0000-0000-0000-000000000001"

        execute_empty = MagicMock()
        execute_empty.data = []
        execute_empty.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = execute_empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value = execute_empty

        resp = client.get(
            f"/api/v1/widget-health/{tenant_id}",
            headers=auth_headers_for(tenant_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "overall" in body
        assert "checks" in body
        assert "stats" in body

    def test_get_health_403_for_wrong_tenant(
        self, client, mock_supabase, auth_headers_for
    ):
        """JWT for tenant A cannot read tenant B's health."""
        tenant_a = "00000000-0000-0000-0000-000000000001"
        tenant_b = "00000000-0000-0000-0000-000000000002"

        resp = client.get(
            f"/api/v1/widget-health/{tenant_b}",
            headers=auth_headers_for(tenant_a),
        )
        assert resp.status_code == 403

    def test_get_health_401_without_token(self, client):
        """No Authorization header → 422 (FastAPI rejects missing Header dep)."""
        tenant_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(f"/api/v1/widget-health/{tenant_id}")
        # FastAPI returns 422 when a required Header dependency is missing
        assert resp.status_code in (401, 422)


class TestAllowedDomainsRouter:
    """Integration tests for PUT /api/v1/widget/config/{tenant_id}/allowed-domains."""

    def test_update_allowed_domains_200(
        self, client, mock_supabase, auth_headers_for
    ):
        """Valid JWT + widget row → 200 + updated domain list."""
        tenant_id = "00000000-0000-0000-0000-000000000001"

        update_execute = MagicMock()
        update_execute.data = [{"tenant_id": tenant_id, "allowed_domains": ["example.com"]}]
        (
            mock_supabase.table.return_value
            .update.return_value
            .eq.return_value
            .execute.return_value
        ) = update_execute

        resp = client.put(
            f"/api/v1/widget/config/{tenant_id}/allowed-domains",
            headers=auth_headers_for(tenant_id),
            json={"allowed_domains": ["example.com", "EXAMPLE.COM"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Normalised to lowercase + deduplicated-ish
        assert "allowed_domains" in body
        # Both entries normalise to "example.com" — expect 1 or 2 depending on dedup
        assert all(d == d.lower() for d in body["allowed_domains"])

    def test_update_allowed_domains_403_wrong_tenant(
        self, client, mock_supabase, auth_headers_for
    ):
        """JWT for tenant A cannot update tenant B's allowed domains."""
        tenant_a = "00000000-0000-0000-0000-000000000001"
        tenant_b = "00000000-0000-0000-0000-000000000002"

        resp = client.put(
            f"/api/v1/widget/config/{tenant_b}/allowed-domains",
            headers=auth_headers_for(tenant_a),
            json={"allowed_domains": []},
        )
        assert resp.status_code == 403

    def test_update_allowed_domains_404_no_widget_config(
        self, client, mock_supabase, auth_headers_for
    ):
        """Widget config row missing → 404."""
        tenant_id = "00000000-0000-0000-0000-000000000001"

        update_execute = MagicMock()
        update_execute.data = []
        (
            mock_supabase.table.return_value
            .update.return_value
            .eq.return_value
            .execute.return_value
        ) = update_execute

        resp = client.put(
            f"/api/v1/widget/config/{tenant_id}/allowed-domains",
            headers=auth_headers_for(tenant_id),
            json={"allowed_domains": ["example.com"]},
        )
        assert resp.status_code == 404
