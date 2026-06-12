"""Tests for GET /api/v1/admin/tenant-health — tenant health board.

Auth pattern mirrors test_admin_funnel.py:
  - Patch backend.routers.admin_health.settings to control the admin secret.
  - Pass x-api-secret header for authenticated requests.

Coverage:
  1. Auth rejection — no header → 401, wrong secret → 401, unconfigured → 401.
  2. Health classification:
     red    — no leads ever + tenant 7+ days old
     red    — drafts rotting (pending_approval older than 48h)
     yellow — no leads in last 7 days
     yellow — pending drafts > 3
     green  — recent leads, small fresh draft queue
     not red — brand-new tenant (<7 days) with no leads
  3. Demo flag passthrough — is_demo surfaces, demo tenants NOT excluded.
  4. Sorting — red rows first, then yellow, then green.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

ADMIN_SECRET = "test-health-secret-1234"
ENDPOINT = "/api/v1/admin/tenant-health"

NOW = datetime.now(timezone.utc)


def _iso(delta: timedelta) -> str:
    """ISO timestamp `delta` in the past."""
    return (NOW - delta).isoformat()


def _mock_db(tenants=None, leads=None, drafts=None):
    """Mock Supabase client routing per-table results.

    Router chains:
        tenants       → .table().select().execute()
        leads         → .table().select().execute()
        os_agent_runs → .table().select().eq().execute()
    """
    results = {
        "tenants": tenants or [],
        "leads": leads or [],
        "os_agent_runs": drafts or [],
    }

    def table(name):
        mock_result = MagicMock()
        mock_result.data = results.get(name, [])
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = mock_result
        return query

    db = MagicMock()
    db.table.side_effect = table
    return db


def _get(client, db, **kwargs):
    with patch(
        "backend.routers.admin_health.get_service_supabase", return_value=db
    ):
        return client.get(
            ENDPOINT, headers={"x-api-secret": ADMIN_SECRET}, **kwargs
        )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi state between tests — endpoint is limited to 10/minute.

    Same pattern as test_login_and_chat.py and test_multi_tenant_isolation.py.
    """
    from backend.limiter import limiter

    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def patch_health_secret():
    """Patch settings so _admin_secret() returns a known value."""
    with patch("backend.routers.admin_health.settings") as mock_s:
        mock_s.admin_api_secret_key = ADMIN_SECRET
        mock_s.api_secret_key = ADMIN_SECRET
        yield mock_s


def _tenant(tenant_id, *, name="Biz", plan="growth", age=timedelta(days=30), is_demo=False):
    return {
        "id": tenant_id,
        "business_name": name,
        "plan": plan,
        "created_at": _iso(age),
        "is_demo": is_demo,
    }


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestHealthAuth:
    def test_no_secret_header_returns_401(self, client):
        res = client.get(ENDPOINT)
        assert res.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        res = client.get(ENDPOINT, headers={"x-api-secret": "wrong-value"})
        assert res.status_code == 401

    def test_missing_secret_in_settings_returns_401(self, client):
        """If admin secret is not configured at all, every call must be rejected."""
        with patch("backend.routers.admin_health.settings") as mock_s:
            mock_s.admin_api_secret_key = ""
            mock_s.api_secret_key = ""
            res = client.get(ENDPOINT, headers={"x-api-secret": ADMIN_SECRET})
            assert res.status_code == 401


# ---------------------------------------------------------------------------
# Health classification
# ---------------------------------------------------------------------------


class TestHealthClassification:
    def _single(self, client, db):
        res = _get(client, db)
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert len(body) == 1
        return body[0]

    def test_red_no_leads_ever_and_7_days_old(self, client):
        db = _mock_db(tenants=[_tenant("t1", age=timedelta(days=10))])
        row = self._single(client, db)
        assert row["health"] == "red"
        assert row["leads_total"] == 0
        assert row["leads_7d"] == 0
        assert row["last_lead_at"] is None

    def test_new_tenant_without_leads_is_not_red(self, client):
        """Tenant younger than 7 days with no leads escapes red (yellow: no leads in 7d)."""
        db = _mock_db(tenants=[_tenant("t1", age=timedelta(days=2))])
        row = self._single(client, db)
        assert row["health"] == "yellow"

    def test_red_when_drafts_rotting(self, client):
        """pending_approval draft older than 48h → red even with recent leads."""
        db = _mock_db(
            tenants=[_tenant("t1")],
            leads=[{"client_id": "t1", "created_at": _iso(timedelta(days=1))}],
            drafts=[{"client_id": "t1", "created_at": _iso(timedelta(hours=72))}],
        )
        row = self._single(client, db)
        assert row["health"] == "red"
        assert row["pending_drafts"] == 1
        assert row["drafts_rotting"] == 1

    def test_fresh_pending_draft_does_not_rot(self, client):
        """pending_approval draft younger than 48h is pending but not rotting."""
        db = _mock_db(
            tenants=[_tenant("t1")],
            leads=[{"client_id": "t1", "created_at": _iso(timedelta(days=1))}],
            drafts=[{"client_id": "t1", "created_at": _iso(timedelta(hours=12))}],
        )
        row = self._single(client, db)
        assert row["health"] == "green"
        assert row["pending_drafts"] == 1
        assert row["drafts_rotting"] == 0

    def test_yellow_no_leads_in_7_days(self, client):
        """Leads exist but the most recent is older than 7 days → yellow."""
        db = _mock_db(
            tenants=[_tenant("t1")],
            leads=[{"client_id": "t1", "created_at": _iso(timedelta(days=20))}],
        )
        row = self._single(client, db)
        assert row["health"] == "yellow"
        assert row["leads_total"] == 1
        assert row["leads_7d"] == 0
        assert row["last_lead_at"] is not None

    def test_yellow_pending_drafts_over_3(self, client):
        """More than 3 fresh pending drafts → yellow even with recent leads."""
        db = _mock_db(
            tenants=[_tenant("t1")],
            leads=[{"client_id": "t1", "created_at": _iso(timedelta(days=1))}],
            drafts=[
                {"client_id": "t1", "created_at": _iso(timedelta(hours=h))}
                for h in (1, 2, 3, 4)
            ],
        )
        row = self._single(client, db)
        assert row["health"] == "yellow"
        assert row["pending_drafts"] == 4
        assert row["drafts_rotting"] == 0

    def test_green_recent_leads_no_problem_drafts(self, client):
        db = _mock_db(
            tenants=[_tenant("t1")],
            leads=[
                {"client_id": "t1", "created_at": _iso(timedelta(days=1))},
                {"client_id": "t1", "created_at": _iso(timedelta(days=20))},
            ],
        )
        row = self._single(client, db)
        assert row["health"] == "green"
        assert row["leads_total"] == 2
        assert row["leads_7d"] == 1

    def test_leads_scoped_per_client_id(self, client):
        """Another tenant's leads must not bleed into this tenant's counts."""
        db = _mock_db(
            tenants=[_tenant("t1", age=timedelta(days=10))],
            leads=[{"client_id": "other", "created_at": _iso(timedelta(days=1))}],
        )
        row = self._single(client, db)
        assert row["leads_total"] == 0
        assert row["health"] == "red"

    def test_empty_platform_returns_empty_list(self, client):
        res = _get(client, _mock_db())
        assert res.status_code == 200
        assert res.json() == []


# ---------------------------------------------------------------------------
# Demo flag passthrough
# ---------------------------------------------------------------------------


class TestDemoFlag:
    def test_demo_tenant_included_and_flagged(self, client):
        db = _mock_db(
            tenants=[
                _tenant("t1", name="Real Biz"),
                _tenant("t2", name="Demo Biz", is_demo=True),
            ],
            leads=[
                {"client_id": "t1", "created_at": _iso(timedelta(days=1))},
                {"client_id": "t2", "created_at": _iso(timedelta(days=1))},
            ],
        )
        res = _get(client, db)
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2  # demo tenant NOT excluded
        by_id = {r["tenant_id"]: r for r in body}
        assert by_id["t1"]["is_demo"] is False
        assert by_id["t2"]["is_demo"] is True

    def test_null_is_demo_coerced_to_false(self, client):
        tenant = _tenant("t1")
        tenant["is_demo"] = None
        db = _mock_db(
            tenants=[tenant],
            leads=[{"client_id": "t1", "created_at": _iso(timedelta(days=1))}],
        )
        res = _get(client, db)
        assert res.json()[0]["is_demo"] is False


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    def test_red_rows_sort_first(self, client):
        db = _mock_db(
            tenants=[
                _tenant("green1", name="Alpha Green"),
                _tenant("red1", name="Beta Red", age=timedelta(days=10)),
                _tenant("yellow1", name="Gamma Yellow"),
            ],
            leads=[
                {"client_id": "green1", "created_at": _iso(timedelta(days=1))},
                {"client_id": "yellow1", "created_at": _iso(timedelta(days=20))},
            ],
        )
        res = _get(client, db)
        assert res.status_code == 200
        healths = [r["health"] for r in res.json()]
        assert healths == ["red", "yellow", "green"]
