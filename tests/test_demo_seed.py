"""Tests for backend.services.demo_seed and backend.services.demo_reset_job.

Uses MagicMock chaining (same pattern as tests/test_documents.py).
No HTTP client needed — calls service functions directly.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Mock DB helpers
# ---------------------------------------------------------------------------

def _make_db():
    """Return a MagicMock whose .table() call returns a chainable table mock."""
    db = MagicMock()
    return db


def _mock_table(data=None, count=None):
    """Return a reusable table mock that yields the given data on .execute()."""
    table = MagicMock()
    result = MagicMock()
    result.data = data if data is not None else []
    result.count = count if count is not None else (len(data) if data else 0)
    # Chain every fluent method back to the table itself
    for method in [
        "select", "insert", "update", "delete", "eq", "neq",
        "gte", "lte", "gt", "lt", "limit", "order", "filter", "is_",
    ]:
        getattr(table, method).return_value = table
    table.execute.return_value = result
    return table


# ---------------------------------------------------------------------------
# ensure_demo_tenant
# ---------------------------------------------------------------------------

class TestEnsureDemoTenant:
    def test_returns_existing_when_found(self):
        from backend.services.demo_seed import ensure_demo_tenant

        db = _make_db()
        tenants_table = _mock_table(data=[{"id": "tid-existing", "business_name": "Demo"}])
        db.table.return_value = tenants_table

        result = ensure_demo_tenant(db)
        assert result == "tid-existing"

    def test_returns_none_on_db_error(self):
        from backend.services.demo_seed import ensure_demo_tenant

        db = _make_db()
        db.table.side_effect = Exception("DB unreachable")

        result = ensure_demo_tenant(db)
        assert result is None

    def test_creates_tenant_when_none_exists(self):
        from backend.services.demo_seed import ensure_demo_tenant

        db = _make_db()
        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            t = _mock_table(data=[])
            if name == "tenants":
                # First call = select (no demo), subsequent = insert
                if call_count["n"] == 1:
                    pass  # returns empty list = "not found"
                else:
                    t = _mock_table(data=[{"id": "new-tid"}])
            return t

        db.table.side_effect = table_side_effect
        # Patch _seed_demo_tenant so we don't actually exercise all the sub-inserts
        with patch(
            "backend.services.demo_seed._seed_demo_tenant",
            return_value="seeded-tid",
        ):
            result = ensure_demo_tenant(db)

        assert result == "seeded-tid"


# ---------------------------------------------------------------------------
# reset_demo_tenant — refuses non-demo tenants
# ---------------------------------------------------------------------------

class TestResetDemoTenantRefusal:
    def test_refuses_when_is_demo_false(self):
        from backend.services.demo_seed import reset_demo_tenant

        db = _make_db()
        tenants_table = _mock_table(data=[{"id": "real-tid", "is_demo": False}])
        db.table.return_value = tenants_table

        result = reset_demo_tenant(db, "real-tid")
        assert result.get("error") == "not a demo tenant"

    def test_refuses_when_tenant_not_found(self):
        from backend.services.demo_seed import reset_demo_tenant

        db = _make_db()
        tenants_table = _mock_table(data=[])
        db.table.return_value = tenants_table

        result = reset_demo_tenant(db, "ghost-tid")
        assert result.get("error") == "tenant not found"

    def test_refuses_on_is_demo_check_exception(self):
        from backend.services.demo_seed import reset_demo_tenant

        db = _make_db()
        db.table.side_effect = Exception("network error")

        result = reset_demo_tenant(db, "some-tid")
        assert result.get("error") == "is_demo check failed"


# ---------------------------------------------------------------------------
# reset_demo_tenant — deletes from correct tables with correct column
# ---------------------------------------------------------------------------

class TestResetDemoTenantDeletion:
    """Verify each volatile table is deleted with the correct tenant column."""

    def _make_demo_db(self, tenant_id="demo-tid"):
        """DB that returns is_demo=True for tenants, then tracks delete calls."""
        db = _make_db()
        deleted_calls: list[tuple[str, str, str]] = []  # (table, column, value)

        def table_side_effect(name):
            t = MagicMock()
            result = MagicMock()
            result.data = []
            result.count = 0
            for method in [
                "select", "insert", "update", "delete",
                "eq", "neq", "gte", "lte", "gt", "lt",
                "limit", "order", "filter", "is_",
            ]:
                getattr(t, method).return_value = t

            if name == "tenants":
                # is_demo check
                result.data = [{"id": tenant_id, "is_demo": True}]
                result.count = 1

            # Track eq calls on delete path
            original_delete = t.delete

            def capturing_eq(col, val):
                deleted_calls.append((name, col, val))
                return t

            t.eq.side_effect = capturing_eq
            t.execute.return_value = result
            return t

        db.table.side_effect = table_side_effect
        return db, deleted_calls

    def test_leads_deleted_with_client_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        # Patch _seed_volatile to avoid side effects
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        lead_calls = [c for c in calls if c[0] == "leads"]
        assert any(c[1] == "client_id" for c in lead_calls), (
            f"leads should be deleted via client_id; got {lead_calls}"
        )

    def test_conversations_deleted_with_client_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        conv_calls = [c for c in calls if c[0] == "conversations"]
        assert any(c[1] == "client_id" for c in conv_calls), (
            f"conversations should be deleted via client_id; got {conv_calls}"
        )

    def test_os_threads_deleted_with_client_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        os_calls = [c for c in calls if c[0] == "os_threads"]
        assert any(c[1] == "client_id" for c in os_calls), (
            f"os_threads should be deleted via client_id; got {os_calls}"
        )

    def test_appointments_deleted_with_tenant_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        appt_calls = [c for c in calls if c[0] == "appointments"]
        assert any(c[1] == "tenant_id" for c in appt_calls), (
            f"appointments should be deleted via tenant_id; got {appt_calls}"
        )

    def test_invoices_deleted_with_tenant_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        inv_calls = [c for c in calls if c[0] == "invoices"]
        assert any(c[1] == "tenant_id" for c in inv_calls), (
            f"invoices should be deleted via tenant_id; got {inv_calls}"
        )

    def test_activity_log_deleted_with_tenant_id(self):
        from backend.services.demo_seed import reset_demo_tenant

        db, calls = self._make_demo_db()
        with patch("backend.services.demo_seed._seed_volatile", return_value={}):
            reset_demo_tenant(db, "demo-tid")

        al_calls = [c for c in calls if c[0] == "activity_log"]
        assert any(c[1] == "tenant_id" for c in al_calls), (
            f"activity_log should be deleted via tenant_id; got {al_calls}"
        )


# ---------------------------------------------------------------------------
# reset_demo_tenants job — time-window gate
# ---------------------------------------------------------------------------

class TestResetDemoTenantsTimeWindow:
    """Job must no-op outside 03:00–05:59 UTC."""

    @pytest.mark.parametrize("hour", [0, 1, 2, 6, 7, 12, 23])
    def test_noop_outside_window(self, hour):
        import asyncio
        from unittest.mock import patch
        from datetime import datetime, timezone

        with patch(
            "backend.services.demo_reset_job.datetime"
        ) as mock_dt, patch(
            "backend.services.demo_reset_job.get_service_supabase"
        ) as mock_db:
            mock_dt.now.return_value = datetime(2026, 6, 12, hour, 0, 0, tzinfo=timezone.utc)
            from backend.services.demo_reset_job import reset_demo_tenants
            result = asyncio.run(reset_demo_tenants())

        assert result == 0
        mock_db.assert_not_called()

    @pytest.mark.parametrize("hour", [3, 4, 5])
    def test_runs_inside_window(self, hour):
        import asyncio
        from unittest.mock import patch
        from datetime import datetime, timezone

        with patch(
            "backend.services.demo_reset_job.datetime"
        ) as mock_dt, patch(
            "backend.services.demo_reset_job.get_service_supabase"
        ) as mock_db, patch(
            "backend.services.demo_reset_job.ensure_demo_tenants",
            return_value={"plumbing": "demo-tid"},
        ), patch(
            "backend.services.demo_reset_job.reset_demo_tenant",
            return_value={"deleted": {}, "seeded": {}},
        ):
            mock_dt.now.return_value = datetime(2026, 6, 12, hour, 30, 0, tzinfo=timezone.utc)
            # Activity-log dedup returns no existing row
            al_table = _mock_table(data=[], count=0)
            db_inst = _make_db()
            db_inst.table.return_value = al_table
            mock_db.return_value = db_inst

            from backend.services.demo_reset_job import reset_demo_tenants
            result = asyncio.run(reset_demo_tenants())

        assert result == 1


# ---------------------------------------------------------------------------
# reset_demo_tenants job — dedup
# ---------------------------------------------------------------------------

class TestResetDemoTenantsDedup:
    """Job must no-op when activity_log says it already ran today."""

    def test_dedup_when_already_ran(self):
        import asyncio
        from unittest.mock import patch
        from datetime import datetime, timezone

        with patch(
            "backend.services.demo_reset_job.datetime"
        ) as mock_dt, patch(
            "backend.services.demo_reset_job.get_service_supabase"
        ) as mock_db, patch(
            "backend.services.demo_reset_job.ensure_demo_tenants",
            return_value={"plumbing": "demo-tid"},
        ) as mock_ensure, patch(
            "backend.services.demo_reset_job.reset_demo_tenant",
        ) as mock_reset:
            mock_dt.now.return_value = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
            # Dedup row already exists
            al_table = _mock_table(data=[{"id": "existing-log"}], count=1)
            db_inst = _make_db()
            db_inst.table.return_value = al_table
            mock_db.return_value = db_inst

            from backend.services.demo_reset_job import reset_demo_tenants
            result = asyncio.run(reset_demo_tenants())

        assert result == 0
        mock_reset.assert_not_called()


# ---------------------------------------------------------------------------
# ensure_demo_tenants — multi-vertical
# ---------------------------------------------------------------------------

class TestEnsureDemoTenantsMultiVertical:
    """The plural API must manage one tenant per vertical definition."""

    def test_returns_existing_tenants_without_reseeding(self):
        from unittest.mock import MagicMock, patch
        from backend.services.demo_seed import ensure_demo_tenants, _DEMO_VERTICALS

        existing = [
            {"id": f"tid-{v}", "owner_email": cfg["owner_email"], "business_type": v}
            for v, cfg in _DEMO_VERTICALS.items()
        ]
        db = MagicMock()
        table = MagicMock()
        for m in ["select", "eq", "limit"]:
            getattr(table, m).return_value = table
        table.execute.return_value = MagicMock(data=existing)
        db.table.return_value = table

        with patch("backend.services.demo_seed._seed_demo_tenant") as mock_seed:
            result = ensure_demo_tenants(db)

        assert set(result.keys()) == set(_DEMO_VERTICALS.keys())
        mock_seed.assert_not_called()

    def test_covers_all_three_verticals(self):
        from backend.services.demo_seed import _DEMO_VERTICALS

        assert set(_DEMO_VERTICALS.keys()) == {"plumbing", "salon", "financial_services"}
        for vertical, cfg in _DEMO_VERTICALS.items():
            assert "(DEMO)" in cfg["business_name"], vertical
            assert cfg["owner_email"] == f"demo-{vertical}@agentnexlify-demo.local", vertical
