"""Tests for the AI-qualifier owner-controls router (GH #216 / migration 147).

Covers GET/PUT /api/v1/qualifier/{tenant_id}: settings read, cross-tenant
rejection, input validation, and the pre-migration resilience (columns may not
exist yet → safe defaults / 503 on write).
"""

from unittest.mock import MagicMock

from backend.tests.conftest import SyncASGITestClient, _make_auth_token
from backend.main import app

_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
_OTHER_ID = "11111111-2222-3333-4444-555555555555"


def _client():
    return SyncASGITestClient(app)


def _auth(tenant_id=_CLIENT_ID):
    return {"Authorization": f"Bearer {_make_auth_token(tenant_id)}"}


def _wire_read(mock_supabase, row):
    res = MagicMock()
    res.data = [row] if row is not None else []
    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute
    ).return_value = res


def _wire_update(mock_supabase, row):
    res = MagicMock()
    res.data = [row] if row is not None else []
    (
        mock_supabase.table.return_value
        .update.return_value
        .eq.return_value
        .execute
    ).return_value = res


class TestGetQualifierSettings:
    def test_returns_settings(self, mock_supabase):
        _wire_read(mock_supabase, {"qualifier_enabled": False, "qualifier_min_intent": 5})
        resp = _client().get(f"/api/v1/qualifier/{_CLIENT_ID}", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["qualifier_enabled"] is False
        assert body["qualifier_min_intent"] == 5

    def test_defaults_when_row_empty(self, mock_supabase):
        _wire_read(mock_supabase, None)
        resp = _client().get(f"/api/v1/qualifier/{_CLIENT_ID}", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["qualifier_enabled"] is True
        assert body["qualifier_min_intent"] == 0

    def test_cross_tenant_forbidden(self, mock_supabase):
        _wire_read(mock_supabase, {"qualifier_enabled": True, "qualifier_min_intent": 0})
        # token is for _CLIENT_ID but we request _OTHER_ID
        resp = _client().get(f"/api/v1/qualifier/{_OTHER_ID}", headers=_auth(_CLIENT_ID))
        assert resp.status_code == 403

    def test_requires_auth(self, mock_supabase):
        resp = _client().get(f"/api/v1/qualifier/{_CLIENT_ID}")
        assert resp.status_code in (401, 403)

    def test_pre_migration_falls_back_to_defaults(self, mock_supabase):
        # Columns not present yet → the read raises and the router returns defaults.
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
            'column "qualifier_enabled" does not exist'
        )
        resp = _client().get(f"/api/v1/qualifier/{_CLIENT_ID}", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["qualifier_enabled"] is True


class TestUpdateQualifierSettings:
    def test_updates_settings(self, mock_supabase):
        _wire_update(mock_supabase, {"id": _CLIENT_ID})
        _wire_read(mock_supabase, {"qualifier_enabled": False, "qualifier_min_intent": 3})
        resp = _client().put(
            f"/api/v1/qualifier/{_CLIENT_ID}",
            json={"qualifier_enabled": False, "qualifier_min_intent": 3},
            headers=_auth(),
        )
        assert resp.status_code == 200
        assert resp.json()["qualifier_min_intent"] == 3

    def test_cross_tenant_forbidden(self, mock_supabase):
        _wire_update(mock_supabase, {"id": _OTHER_ID})
        resp = _client().put(
            f"/api/v1/qualifier/{_OTHER_ID}",
            json={"qualifier_enabled": True, "qualifier_min_intent": 0},
            headers=_auth(_CLIENT_ID),
        )
        assert resp.status_code == 403

    def test_out_of_range_rejected(self, mock_supabase):
        resp = _client().put(
            f"/api/v1/qualifier/{_CLIENT_ID}",
            json={"qualifier_enabled": True, "qualifier_min_intent": 11},
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_missing_tenant_returns_404(self, mock_supabase):
        _wire_update(mock_supabase, None)  # update affected no rows
        resp = _client().put(
            f"/api/v1/qualifier/{_CLIENT_ID}",
            json={"qualifier_enabled": True, "qualifier_min_intent": 0},
            headers=_auth(),
        )
        assert resp.status_code == 404

    def test_pre_migration_returns_503(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception(
            'column "qualifier_enabled" does not exist'
        )
        resp = _client().put(
            f"/api/v1/qualifier/{_CLIENT_ID}",
            json={"qualifier_enabled": True, "qualifier_min_intent": 0},
            headers=_auth(),
        )
        assert resp.status_code == 503
