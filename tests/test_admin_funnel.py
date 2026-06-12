"""Tests for GET /api/v1/admin/funnel/wizard — signup-funnel readout.

Auth pattern mirrors test_admin_analytics.py:
  - Patch backend.routers.admin_funnel.settings to control the admin secret.
  - Pass x-api-secret header for authenticated requests.

Coverage:
  1. Auth rejection — no header → 401.
  2. Auth rejection — wrong secret → 401.
  3. Happy path — returns correct shape with aggregated data.
  4. ?days= param capping — values > 90 are silently capped to 90.
  5. Empty result — no events in window → empty steps/dropoff, zero totals.
  6. Distinct-tenant counting — same tenant on same step counted once.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.main import app

ADMIN_SECRET = "test-funnel-secret-9876"
ENDPOINT = "/api/v1/admin/funnel/wizard"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def patch_funnel_secret():
    """Patch settings so _admin_secret() returns a known value."""
    with patch("backend.routers.admin_funnel.settings") as mock_s:
        mock_s.admin_api_secret_key = ADMIN_SECRET
        mock_s.api_secret_key = ADMIN_SECRET
        yield mock_s


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestFunnelAuth:
    def test_no_secret_header_returns_401(self, client):
        res = client.get(ENDPOINT)
        assert res.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        res = client.get(ENDPOINT, headers={"x-api-secret": "wrong-value"})
        assert res.status_code == 401

    def test_missing_secret_in_settings_returns_401(self, client):
        """If admin secret is not configured at all, every call must be rejected."""
        with patch("backend.routers.admin_funnel.settings") as mock_s:
            mock_s.admin_api_secret_key = ""
            mock_s.api_secret_key = ""
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})
            assert res.status_code == 401


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestFunnelHappyPath:
    def _mock_db(self, rows):
        """Return a mock Supabase client whose wizard_events query returns rows."""
        mock_result = MagicMock()
        mock_result.data = rows

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.execute.return_value = mock_result

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value = mock_query
        return mock_db

    def test_happy_path_returns_correct_shape(self, client):
        """With events for steps 0 and 7, shape and values must be correct."""
        rows = [
            {"tenant_id": "t1", "step": 0},
            {"tenant_id": "t2", "step": 0},
            {"tenant_id": "t1", "step": 7},
        ]
        mock_db = self._mock_db(rows)

        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})

        assert res.status_code == 200
        body = res.json()

        # Top-level keys present.
        assert "window_days" in body
        assert "steps" in body
        assert "dropoff" in body
        assert "totals" in body

        # window_days defaults to 30.
        assert body["window_days"] == 30

        # Steps: only 0 and 7 had events.
        step_nums = [s["step"] for s in body["steps"]]
        assert 0 in step_nums
        assert 7 in step_nums

        step_0 = next(s for s in body["steps"] if s["step"] == 0)
        assert step_0["tenants"] == 2
        assert step_0["label"] == "express chooser"

        step_7 = next(s for s in body["steps"] if s["step"] == 7)
        assert step_7["tenants"] == 1
        assert step_7["label"] == "embed"

        # Totals.
        totals = body["totals"]
        assert totals["started"] == 2
        assert totals["completed"] == 1
        assert totals["completion_rate"] == 0.5

        # Drop-off between step 0 and step 7.
        assert len(body["dropoff"]) == 1
        drop = body["dropoff"][0]
        assert drop["from_step"] == 0
        assert drop["to_step"] == 7
        assert drop["lost"] == 1
        assert drop["rate"] == 0.5

    def test_distinct_tenant_counting(self, client):
        """Same tenant entering the same step multiple times counted once."""
        rows = [
            {"tenant_id": "t1", "step": 0},
            {"tenant_id": "t1", "step": 0},  # duplicate — must not double-count
            {"tenant_id": "t2", "step": 0},
        ]
        mock_db = self._mock_db(rows)

        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})

        assert res.status_code == 200
        body = res.json()
        step_0 = next(s for s in body["steps"] if s["step"] == 0)
        assert step_0["tenants"] == 2  # t1 and t2, not 3

    def test_empty_events_returns_zero_totals(self, client):
        """No events in window → empty steps, empty dropoff, zero totals."""
        mock_db = self._mock_db([])

        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})

        assert res.status_code == 200
        body = res.json()
        assert body["steps"] == []
        assert body["dropoff"] == []
        assert body["totals"]["started"] == 0
        assert body["totals"]["completed"] == 0
        assert body["totals"]["completion_rate"] == 0.0


# ---------------------------------------------------------------------------
# ?days= param capping
# ---------------------------------------------------------------------------


class TestFunnelDaysParam:
    def _mock_db(self):
        mock_result = MagicMock()
        mock_result.data = []
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value = mock_query
        return mock_db

    def test_days_param_used_within_limit(self, client):
        """?days=7 should return window_days=7."""
        mock_db = self._mock_db()
        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(
                ENDPOINT, params={"days": 7}, headers={"x-api-secret": ADMIN_SECRET}
            )
        assert res.status_code == 200
        assert res.json()["window_days"] == 7

    def test_days_param_capped_at_90(self, client):
        """?days=200 must be silently capped to 90."""
        mock_db = self._mock_db()
        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(
                ENDPOINT, params={"days": 200}, headers={"x-api-secret": ADMIN_SECRET}
            )
        assert res.status_code == 200
        assert res.json()["window_days"] == 90

    def test_days_param_default_is_30(self, client):
        """No ?days param → window_days=30."""
        mock_db = self._mock_db()
        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})
        assert res.status_code == 200
        assert res.json()["window_days"] == 30

    def test_days_param_zero_rejected(self, client):
        """?days=0 is below ge=1 constraint — FastAPI should return 422."""
        mock_db = self._mock_db()
        with patch("backend.routers.admin_funnel.get_service_supabase", return_value=mock_db):
            res = client.get(
                ENDPOINT, params={"days": 0}, headers={"x-api-secret": ADMIN_SECRET}
            )
        assert res.status_code == 422
