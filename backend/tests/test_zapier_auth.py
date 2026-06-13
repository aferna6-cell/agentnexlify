"""Tests for Zapier API key auth — #58.

Tests cover:
  - generate_api_key() format + bcrypt verify
  - validate_api_key() happy path + prefix mismatch + revoked key
  - POST /api/zapier/keys (JWT auth, tier gate)
  - GET  /api/zapier/keys (JWT auth, lists keys)
  - DELETE /api/zapier/keys/{key_id} (JWT auth, revoke)
  - GET /api/zapier/leads/new (API key auth, tier gate, Free blocked)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import backend.models.database as _db_module
from backend.tests.conftest import (
    SyncASGITestClient,
    _make_auth_token,
)
from backend.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
_KEY_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_NOW = datetime.now(timezone.utc).isoformat()


def _make_client():
    return SyncASGITestClient(app)


def _growth_headers():
    return {"Authorization": f"Bearer {_make_auth_token(_CLIENT_ID)}"}


# ---------------------------------------------------------------------------
# Unit tests: generate_api_key
# ---------------------------------------------------------------------------


class TestGenerateApiKey:
    def test_key_format(self):
        from backend.services.api_key_auth import generate_api_key

        raw, key_hash, key_prefix = generate_api_key()
        assert raw.startswith("zap_")
        assert len(raw) > 8
        assert len(key_prefix) == 8
        assert key_prefix == raw[:8]

    def test_bcrypt_hash_verifiable(self):
        import bcrypt
        from backend.services.api_key_auth import generate_api_key

        raw, key_hash, _ = generate_api_key()
        assert bcrypt.checkpw(raw.encode(), key_hash.encode())

    def test_bcrypt_cost_12(self):
        from backend.services.api_key_auth import generate_api_key

        _, key_hash, _ = generate_api_key()
        # bcrypt hash format: $2b$<cost>$<salt+hash>
        cost_part = key_hash.split("$")[2]
        assert cost_part == "12", f"Expected cost 12, got {cost_part}"

    def test_unique_keys(self):
        from backend.services.api_key_auth import generate_api_key

        raw1, _, _ = generate_api_key()
        raw2, _, _ = generate_api_key()
        assert raw1 != raw2


# ---------------------------------------------------------------------------
# Unit tests: validate_api_key
# ---------------------------------------------------------------------------


class TestValidateApiKey:
    def test_returns_none_for_empty_key(self):
        from backend.services.api_key_auth import validate_api_key

        assert validate_api_key("") is None
        assert validate_api_key("zap_") is None  # too short

    def test_returns_row_on_valid_key(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key, validate_api_key
        import bcrypt

        raw, key_hash, key_prefix = generate_api_key()

        # Stub DB to return matching row
        row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": "Test Key",
            "last_used_at": None,
            "revoked_at": None,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [row]

        result = validate_api_key(raw)
        assert result is not None
        assert result["id"] == _KEY_ID
        assert result["client_id"] == _CLIENT_ID

    def test_returns_none_on_hash_mismatch(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key, validate_api_key

        raw, key_hash, key_prefix = generate_api_key()
        different_raw, different_hash, _ = generate_api_key()

        # Row has hash for a DIFFERENT key
        row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": different_hash,
            "key_prefix": key_prefix,
            "name": "Test Key",
            "last_used_at": None,
            "revoked_at": None,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [row]

        result = validate_api_key(raw)
        assert result is None

    def test_returns_none_when_no_prefix_match(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key, validate_api_key

        raw, _, _ = generate_api_key()
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        result = validate_api_key(raw)
        assert result is None


# ---------------------------------------------------------------------------
# API endpoint tests: POST /api/zapier/keys
# ---------------------------------------------------------------------------


class TestCreateApiKey:
    def test_creates_key_for_growth_tenant(self, mock_supabase):
        client = _make_client()

        # Tenant DB row (plan check)
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"plan": "growth"}
        ]
        # Insert returns key row
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": _KEY_ID,
                "client_id": _CLIENT_ID,
                "name": "My Zap",
                "key_prefix": "zap_aaaa",
                "created_at": _NOW,
            }
        ]

        resp = client.post(
            "/api/zapier/keys",
            json={"name": "My Zap"},
            headers=_growth_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("zap_")
        assert data["client_id"] == _CLIENT_ID

    def test_blocks_free_tenant(self, mock_supabase):
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"plan": "free"}
        ]

        resp = client.post(
            "/api/zapier/keys",
            json={"name": "My Zap"},
            headers=_growth_headers(),
        )
        assert resp.status_code == 402

    def test_requires_auth(self, mock_supabase):
        client = _make_client()
        resp = client.post("/api/zapier/keys", json={"name": "My Zap"})
        assert resp.status_code == 422  # missing Authorization header

    def test_professional_tenant_allowed(self, mock_supabase):
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"plan": "professional"}
        ]
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": _KEY_ID,
                "client_id": _CLIENT_ID,
                "name": "Pro Zap",
                "key_prefix": "zap_bbbb",
                "created_at": _NOW,
            }
        ]

        resp = client.post(
            "/api/zapier/keys",
            json={"name": "Pro Zap"},
            headers=_growth_headers(),
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# API endpoint tests: GET /api/zapier/keys
# ---------------------------------------------------------------------------


class TestListApiKeys:
    def test_lists_keys_for_tenant(self, mock_supabase):
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": _KEY_ID,
                "client_id": _CLIENT_ID,
                "name": "Zap Key 1",
                "key_prefix": "zap_aaaa",
                "last_used_at": None,
                "created_at": _NOW,
                "revoked_at": None,
            }
        ]

        resp = client.get("/api/zapier/keys", headers=_growth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["key_prefix"] == "zap_aaaa"
        # Must NOT expose key_hash
        assert "key_hash" not in data[0]


# ---------------------------------------------------------------------------
# API endpoint tests: DELETE /api/zapier/keys/{key_id}
# ---------------------------------------------------------------------------


class TestRevokeApiKey:
    def test_revokes_owned_key(self, mock_supabase):
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": _KEY_ID, "client_id": _CLIENT_ID, "revoked_at": None}
        ]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        resp = client.delete(
            f"/api/zapier/keys/{_KEY_ID}",
            headers=_growth_headers(),
        )
        assert resp.status_code == 204

    def test_404_for_missing_key(self, mock_supabase):
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        resp = client.delete(
            f"/api/zapier/keys/{_KEY_ID}",
            headers=_growth_headers(),
        )
        assert resp.status_code == 404

    def test_idempotent_already_revoked(self, mock_supabase):
        """Revoking an already-revoked key returns 204 (idempotent)."""
        client = _make_client()

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": _KEY_ID, "client_id": _CLIENT_ID, "revoked_at": _NOW}
        ]

        resp = client.delete(
            f"/api/zapier/keys/{_KEY_ID}",
            headers=_growth_headers(),
        )
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# API endpoint tests: GET /api/zapier/leads/new
# ---------------------------------------------------------------------------


class TestGetNewLeads:
    def _key_auth_headers(self, raw_key: str) -> dict:
        return {"x-api-key": raw_key}

    def test_free_tier_blocked(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key
        import bcrypt

        client = _make_client()
        raw, key_hash, key_prefix = generate_api_key()

        key_row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        }
        # validate_api_key prefix lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [key_row]

        # tenant lookup returns free plan
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": _CLIENT_ID, "plan": "free", "plan_status": "active"}
        ]

        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "2026-01-01T00:00:00Z"},
            headers=self._key_auth_headers(raw),
        )
        assert resp.status_code == 402

    def test_cancelled_subscription_blocked(self, mock_supabase):
        # GH #107: a churned tenant (paid plan, plan_status='cancelled') must
        # lose Zapier access even though the plan tier still gates open.
        from backend.services.api_key_auth import generate_api_key

        client = _make_client()
        raw, key_hash, key_prefix = generate_api_key()

        key_row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [key_row]
        # paid plan but cancelled subscription
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": _CLIENT_ID, "plan": "growth", "plan_status": "cancelled"}
        ]

        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "2026-01-01T00:00:00Z"},
            headers=self._key_auth_headers(raw),
        )
        assert resp.status_code == 402

    def test_invalid_key_returns_401(self, mock_supabase):
        client = _make_client()
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "2026-01-01T00:00:00Z"},
            headers=self._key_auth_headers("zap_badbadbadbadbad"),
        )
        assert resp.status_code == 401

    def test_invalid_since_returns_400(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key

        client = _make_client()
        raw, key_hash, key_prefix = generate_api_key()

        key_row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [key_row]
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": _CLIENT_ID, "plan": "growth", "plan_status": "active"}
        ]
        # touch_last_used call
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "not-a-date"},
            headers=self._key_auth_headers(raw),
        )
        assert resp.status_code == 400

    def test_growth_tier_returns_leads(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key

        client = _make_client()
        raw, key_hash, key_prefix = generate_api_key()

        key_row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        }

        lead_row = {
            "id": "lead-111",
            "client_id": _CLIENT_ID,
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "555-0100",
            "areas_of_interest": ["hvac", "repair"],
            "status": "new",
            "created_at": _NOW,
        }

        call_count = 0

        def _table_side_effect(table_name):
            mock = MagicMock()
            if table_name == "tenant_api_keys":
                # prefix lookup
                mock.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [key_row]
                # touch last_used update
                mock.update.return_value.eq.return_value.execute.return_value.data = []
            elif table_name == "tenants":
                mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": _CLIENT_ID, "plan": "growth", "plan_status": "active"}
                ]
            elif table_name == "leads":
                mock.select.return_value.eq.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value.data = [lead_row]
            return mock

        mock_supabase.table.side_effect = _table_side_effect

        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "2026-01-01T00:00:00Z"},
            headers=self._key_auth_headers(raw),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Alice"
        # arrays joined with semicolon
        assert data[0]["areas_of_interest"] == "hvac;repair"


# ---------------------------------------------------------------------------
# Tier gating: all allowed tiers
# ---------------------------------------------------------------------------


class TestAllowedTiers:
    def test_allowed_plans_constant(self):
        from backend.services.api_key_auth import _ALLOWED_PLANS

        assert "growth" in _ALLOWED_PLANS
        assert "autopilot" in _ALLOWED_PLANS
        assert "professional" in _ALLOWED_PLANS
        assert "enterprise" in _ALLOWED_PLANS
        assert "free" not in _ALLOWED_PLANS


# ---------------------------------------------------------------------------
# Rate limiter — in-memory per-prefix counter (per-process)
# ---------------------------------------------------------------------------


class TestApiKeyLimiter:
    def setup_method(self):
        from backend.services import api_key_limiter

        api_key_limiter.reset_for_tests()

    def test_first_request_allowed(self):
        from backend.services.api_key_limiter import check_and_increment

        allowed, count = check_and_increment("zap_aaaa", limit_per_minute=100)
        assert allowed is True
        assert count == 1

    def test_under_limit_allowed(self):
        from backend.services.api_key_limiter import check_and_increment

        for i in range(99):
            allowed, _ = check_and_increment("zap_bbbb", limit_per_minute=100)
            assert allowed is True
        allowed, count = check_and_increment("zap_bbbb", limit_per_minute=100)
        assert allowed is True
        assert count == 100

    def test_over_limit_rejected(self):
        from backend.services.api_key_limiter import check_and_increment

        for _ in range(100):
            check_and_increment("zap_cccc", limit_per_minute=100)
        allowed, count = check_and_increment("zap_cccc", limit_per_minute=100)
        assert allowed is False
        assert count == 101

    def test_separate_prefixes_independent(self):
        from backend.services.api_key_limiter import check_and_increment

        for _ in range(100):
            check_and_increment("zap_dddd", limit_per_minute=100)
        # Different prefix should still be allowed
        allowed, _ = check_and_increment("zap_eeee", limit_per_minute=100)
        assert allowed is True

    def test_resets_next_minute(self, monkeypatch):
        import backend.services.api_key_limiter as lim

        base = 1_700_000_000
        monkeypatch.setattr(lim.time, "time", lambda: float(base))
        for _ in range(100):
            lim.check_and_increment("zap_ffff", limit_per_minute=100)
        allowed, _ = lim.check_and_increment("zap_ffff", limit_per_minute=100)
        assert allowed is False

        # Advance 60s into next bucket
        monkeypatch.setattr(lim.time, "time", lambda: float(base + 60))
        allowed, count = lim.check_and_increment("zap_ffff", limit_per_minute=100)
        assert allowed is True
        assert count == 1

    def test_fail_open_on_exception(self, monkeypatch):
        """Limiter must fail-open: if internal error, allow request + log."""
        import backend.services.api_key_limiter as lim

        class _BoomDict:
            def setdefault(self, *_a, **_kw):
                raise RuntimeError("simulated infra failure")

        monkeypatch.setattr(lim, "_BUCKETS", _BoomDict())
        allowed, count = lim.check_and_increment("zap_gggg", limit_per_minute=100)
        assert allowed is True
        assert count == 0


# ---------------------------------------------------------------------------
# Rate limit integration: GET /api/zapier/leads/new
# ---------------------------------------------------------------------------


class TestRateLimitIntegration:
    def setup_method(self):
        from backend.services import api_key_limiter

        api_key_limiter.reset_for_tests()

    def _key_auth_headers(self, raw_key: str) -> dict:
        return {"x-api-key": raw_key}

    def test_429_after_limit(self, mock_supabase):
        from backend.services.api_key_auth import generate_api_key

        client = _make_client()
        raw, key_hash, key_prefix = generate_api_key()

        key_row = {
            "id": _KEY_ID,
            "client_id": _CLIENT_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "rate_limit_rpm": 3,  # tight limit for fast test
        }

        def _table_side_effect(table_name):
            mock = MagicMock()
            if table_name == "tenant_api_keys":
                mock.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [key_row]
                mock.update.return_value.eq.return_value.execute.return_value.data = []
            elif table_name == "tenants":
                mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": _CLIENT_ID, "plan": "growth", "plan_status": "active"}
                ]
            elif table_name == "leads":
                mock.select.return_value.eq.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            return mock

        mock_supabase.table.side_effect = _table_side_effect

        # First 3 should succeed
        for i in range(3):
            resp = client.get(
                "/api/zapier/leads/new",
                params={"since": "2026-01-01T00:00:00Z"},
                headers=self._key_auth_headers(raw),
            )
            assert resp.status_code == 200, f"req {i+1} got {resp.status_code}"

        # 4th hits limit
        resp = client.get(
            "/api/zapier/leads/new",
            params={"since": "2026-01-01T00:00:00Z"},
            headers=self._key_auth_headers(raw),
        )
        assert resp.status_code == 429
        assert "retry-after" in {k.lower() for k in resp.headers.keys()}
