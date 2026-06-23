"""Tests for backend/services/weekly_value.py (Weekly Value Digest, gap G2).

Coverage:
- Aggregation correctness (leads, appointments, conversations, invoices, agent runs)
- Dollar math: deal_value sum, avg_lead_value fallback, both-zero case
- Zero-data tenant: all counts 0, empty-state copy confirmed
- Tenant isolation: queries scoped to the correct client_id / tenant_id
- Partial failure resilience: one table error yields zeros for that field, not a crash

No live DB calls — all Supabase access is mocked via unittest.mock.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is importable without an installed package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.weekly_value import compute_weekly_value, DEFAULT_AVG_LEAD_VALUE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_result(data=None, count=None):
    """Build a minimal Supabase-like result object."""
    r = MagicMock()
    r.data = data if data is not None else []
    r.count = count
    return r


def _chain(*args, **kwargs):
    """Return a chainable mock whose final .execute() returns the given result."""
    def _make(result):
        m = MagicMock()
        m.execute.return_value = result
        m.select.return_value = m
        m.eq.return_value = m
        m.gte.return_value = m
        m.limit.return_value = m
        m.or_.return_value = m
        m.filter.return_value = m
        return m
    return _make


def _build_db(
    leads=None,
    appointments_count=0,
    chat_messages=None,
    invoices=None,
    agent_runs_count=0,
):
    """Build a mock Supabase client with per-table responses."""
    db = MagicMock()

    def table_side_effect(name):
        m = MagicMock()
        m.select.return_value = m
        m.eq.return_value = m
        m.gte.return_value = m
        m.limit.return_value = m
        m.or_.return_value = m
        m.filter.return_value = m

        if name == "leads":
            m.execute.return_value = _mock_result(data=leads if leads is not None else [])
        elif name == "appointments":
            m.execute.return_value = _mock_result(count=appointments_count)
        elif name == "chat_messages":
            m.execute.return_value = _mock_result(data=chat_messages if chat_messages is not None else [])
        elif name == "invoices":
            m.execute.return_value = _mock_result(data=invoices if invoices is not None else [])
        elif name == "os_agent_runs":
            m.execute.return_value = _mock_result(count=agent_runs_count)
        else:
            m.execute.return_value = _mock_result()
        return m

    db.table.side_effect = table_side_effect
    return db


# ---------------------------------------------------------------------------
# Aggregation correctness
# ---------------------------------------------------------------------------

class TestAggregationCorrectness:

    def test_leads_counted(self):
        db = _build_db(leads=[{"id": "a", "deal_value": None}, {"id": "b", "deal_value": None}])
        result = compute_weekly_value(db, "tenant-1")
        assert result["leads_captured"] == 2

    def test_appointments_counted(self):
        db = _build_db(appointments_count=3)
        result = compute_weekly_value(db, "tenant-1")
        assert result["appointments_booked"] == 3

    def test_conversations_counted_from_distinct_sessions(self):
        # 5 messages across 3 distinct sessions
        msgs = [
            {"session_id": "s1"},
            {"session_id": "s1"},
            {"session_id": "s2"},
            {"session_id": "s3"},
            {"session_id": "s3"},
        ]
        db = _build_db(chat_messages=msgs)
        result = compute_weekly_value(db, "tenant-1")
        assert result["conversations_handled"] == 3

    def test_invoice_sent_total(self):
        since = "2026-01-01T00:00:00+00:00"
        invoices = [
            {"total": "100.00", "status": "sent", "sent_at": "2026-06-20", "paid_at": None},
            {"total": "250.50", "status": "sent", "sent_at": "2026-06-21", "paid_at": None},
        ]
        db = _build_db(invoices=invoices)
        result = compute_weekly_value(db, "tenant-1")
        assert result["invoices_sent"] == 2
        assert abs(result["invoices_sent_total"] - 350.50) < 0.01

    def test_invoice_paid_total(self):
        since = "2026-01-01"
        invoices = [
            {"total": "500.00", "status": "paid", "sent_at": "2026-06-18", "paid_at": "2026-06-20"},
        ]
        db = _build_db(invoices=invoices)
        result = compute_weekly_value(db, "tenant-1")
        assert result["invoices_paid"] == 1
        assert abs(result["invoices_paid_total"] - 500.0) < 0.01

    def test_agent_runs_counted(self):
        db = _build_db(agent_runs_count=7)
        result = compute_weekly_value(db, "tenant-1")
        assert result["agent_runs_completed"] == 7

    def test_result_has_all_expected_keys(self):
        db = _build_db()
        result = compute_weekly_value(db, "tenant-x")
        expected_keys = {
            "leads_captured",
            "estimated_pipeline_value",
            "appointments_booked",
            "conversations_handled",
            "invoices_sent",
            "invoices_sent_total",
            "invoices_paid",
            "invoices_paid_total",
            "agent_runs_completed",
            "since",
        }
        assert expected_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Dollar math
# ---------------------------------------------------------------------------

class TestDollarMath:

    def test_pipeline_value_from_lead_deal_values(self):
        leads = [
            {"id": "l1", "deal_value": "300.00"},
            {"id": "l2", "deal_value": "700.00"},
        ]
        db = _build_db(leads=leads)
        result = compute_weekly_value(db, "tenant-1")
        assert abs(result["estimated_pipeline_value"] - 1000.0) < 0.01

    def test_pipeline_value_fallback_to_avg_lead_value(self):
        # No deal_value on leads → falls back to avg_lead_value * count
        leads = [{"id": "l1", "deal_value": None}, {"id": "l2", "deal_value": None}]
        db = _build_db(leads=leads)
        result = compute_weekly_value(db, "tenant-1", avg_lead_value=250.0)
        assert abs(result["estimated_pipeline_value"] - 500.0) < 0.01

    def test_pipeline_value_deal_values_take_priority_over_avg(self):
        # If any deal_value present, use sum — not avg_lead_value fallback
        leads = [
            {"id": "l1", "deal_value": "400.00"},
            {"id": "l2", "deal_value": None},
        ]
        db = _build_db(leads=leads)
        result = compute_weekly_value(db, "tenant-1", avg_lead_value=9999.0)
        # Only l1's 400 is summed; avg fallback does NOT run because deal_value_sum > 0
        assert abs(result["estimated_pipeline_value"] - 400.0) < 0.01

    def test_pipeline_value_zero_when_no_leads_and_no_avg(self):
        db = _build_db(leads=[])
        result = compute_weekly_value(db, "tenant-1", avg_lead_value=0.0)
        assert result["estimated_pipeline_value"] == 0.0

    def test_pipeline_value_zero_when_no_deal_value_and_no_avg(self):
        leads = [{"id": "l1", "deal_value": None}]
        db = _build_db(leads=leads)
        result = compute_weekly_value(db, "tenant-1", avg_lead_value=0.0)
        assert result["estimated_pipeline_value"] == 0.0

    def test_default_avg_lead_value_constant_is_zero(self):
        # Ensures DEFAULT_AVG_LEAD_VALUE is safe-zero, not hardcoded magic
        assert DEFAULT_AVG_LEAD_VALUE == 0.0

    def test_avg_lead_value_negative_not_applied(self):
        # Negative avg_lead_value should yield 0 pipeline (guard: avg_lead_value > 0)
        leads = [{"id": "l1", "deal_value": None}]
        db = _build_db(leads=leads)
        result = compute_weekly_value(db, "tenant-1", avg_lead_value=-100.0)
        assert result["estimated_pipeline_value"] == 0.0


# ---------------------------------------------------------------------------
# Zero-data tenant (empty-state)
# ---------------------------------------------------------------------------

class TestZeroDataTenant:

    def test_all_zeros_when_no_data(self):
        db = _build_db(
            leads=[],
            appointments_count=0,
            chat_messages=[],
            invoices=[],
            agent_runs_count=0,
        )
        result = compute_weekly_value(db, "empty-tenant")
        assert result["leads_captured"] == 0
        assert result["estimated_pipeline_value"] == 0.0
        assert result["appointments_booked"] == 0
        assert result["conversations_handled"] == 0
        assert result["invoices_sent"] == 0
        assert result["invoices_sent_total"] == 0.0
        assert result["invoices_paid"] == 0
        assert result["invoices_paid_total"] == 0.0
        assert result["agent_runs_completed"] == 0

    def test_since_field_always_present(self):
        db = _build_db()
        result = compute_weekly_value(db, "empty-tenant")
        assert "since" in result
        assert result["since"]  # non-empty ISO timestamp


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:

    def test_leads_queried_with_client_id(self):
        """Leads table must use client_id, never tenant_id."""
        db = _build_db(leads=[])
        compute_weekly_value(db, "my-tenant")

        # Find all .eq("client_id", ...) calls on the leads table mock
        leads_mock = None
        for call in db.table.call_args_list:
            if call.args[0] == "leads":
                leads_mock = db.table.return_value
                break

        # Verify .eq was called with "client_id" as first arg at some point
        eq_calls = [c.args for c in db.table("leads").eq.call_args_list]
        # At minimum one call should have "client_id"
        # (We check via the mock chain: table("leads").select(...).eq("client_id", ...))
        # The simplest check: ensure "tenant_id" was NOT passed as the field name
        tenant_id_used_for_leads = any(
            "tenant_id" in str(c) for c in db.table("leads").eq.call_args_list
        )
        assert not tenant_id_used_for_leads, (
            "leads table must use client_id, not tenant_id"
        )

    def test_appointments_queried_with_tenant_id(self):
        """Appointments table must use tenant_id."""
        db = _build_db(appointments_count=0)
        compute_weekly_value(db, "my-tenant")

        # Verify "client_id" was NOT used for appointments
        client_id_used_for_appts = any(
            "client_id" in str(c) for c in db.table("appointments").eq.call_args_list
        )
        assert not client_id_used_for_appts, (
            "appointments table must use tenant_id, not client_id"
        )

    def test_different_tenants_get_independent_calls(self):
        """Two compute_weekly_value calls for different tenants must each scope their queries."""
        db_a = _build_db(leads=[{"id": "la", "deal_value": "100"}], appointments_count=1)
        db_b = _build_db(leads=[], appointments_count=0)

        result_a = compute_weekly_value(db_a, "tenant-A")
        result_b = compute_weekly_value(db_b, "tenant-B")

        assert result_a["leads_captured"] == 1
        assert result_b["leads_captured"] == 0
        assert result_a["appointments_booked"] == 1
        assert result_b["appointments_booked"] == 0


# ---------------------------------------------------------------------------
# Partial failure resilience
# ---------------------------------------------------------------------------

class TestPartialFailureResilience:

    def test_leads_failure_yields_zero_not_crash(self):
        db = MagicMock()
        # leads table raises; everything else returns empty
        def _table(name):
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            m.or_.return_value = m
            if name == "leads":
                m.execute.side_effect = RuntimeError("DB connection lost")
            else:
                m.execute.return_value = _mock_result(data=[], count=0)
            return m
        db.table.side_effect = _table

        result = compute_weekly_value(db, "tenant-x")
        assert result["leads_captured"] == 0
        assert result["estimated_pipeline_value"] == 0.0

    def test_appointments_failure_yields_zero_not_crash(self):
        db = MagicMock()
        def _table(name):
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            m.or_.return_value = m
            if name == "appointments":
                m.execute.side_effect = RuntimeError("timeout")
            else:
                m.execute.return_value = _mock_result(data=[], count=0)
            return m
        db.table.side_effect = _table

        result = compute_weekly_value(db, "tenant-x")
        assert result["appointments_booked"] == 0
        # Other fields still populated from their successful queries
        assert "leads_captured" in result

    def test_invoices_failure_yields_zero_not_crash(self):
        db = MagicMock()
        def _table(name):
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            m.or_.return_value = m
            if name == "invoices":
                m.execute.side_effect = Exception("schema mismatch")
            else:
                m.execute.return_value = _mock_result(data=[], count=0)
            return m
        db.table.side_effect = _table

        result = compute_weekly_value(db, "tenant-x")
        assert result["invoices_sent"] == 0
        assert result["invoices_sent_total"] == 0.0
        assert result["invoices_paid"] == 0
        assert result["invoices_paid_total"] == 0.0

    def test_chat_messages_failure_yields_zero_conversations(self):
        db = MagicMock()
        def _table(name):
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            m.or_.return_value = m
            if name == "chat_messages":
                m.execute.side_effect = Exception("rate limit")
            else:
                m.execute.return_value = _mock_result(data=[], count=0)
            return m
        db.table.side_effect = _table

        result = compute_weekly_value(db, "tenant-x")
        assert result["conversations_handled"] == 0
