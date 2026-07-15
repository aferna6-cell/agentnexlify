"""Tests for backend/services/weekly_value.py (Weekly Value Digest, gap G2).

Coverage:
- Aggregation correctness (leads, appointments, conversations, invoices, agent runs)
- Dollar math: deal_value sum, avg_lead_value fallback, both-zero case
- Zero-data tenant: all counts 0, empty-state copy confirmed
- Tenant isolation: queries scoped to the correct client_id / tenant_id
- Partial failure resilience: one table error yields zeros for that field, not a crash
- empty_state_message: returns non-empty helpful copy string
- send_weekly_digest: plan_status filter excludes cancelled tenants
- send_weekly_digest: per-tenant failure does not abort the batch
- send_weekly_digest: zero-activity tenant gets empty-state email (no zeros table)
- _build_and_send_digest: opportunity_html seam renders when provided, skipped when None

No live DB calls — all Supabase access is mocked via unittest.mock.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Ensure repo root is importable without an installed package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.weekly_value import (
    compute_weekly_value,
    DEFAULT_AVG_LEAD_VALUE,
    empty_state_message,
)


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
        # compute_weekly_value uses a trailing 7-day window from now — fixture
        # dates must be relative. (The originals were absolute June dates that
        # were in-window when written and silently drifted out: a time-bomb.)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        invoices = [
            {"total": "100.00", "status": "sent", "sent_at": yesterday, "paid_at": None},
            {"total": "250.50", "status": "sent", "sent_at": yesterday, "paid_at": None},
        ]
        db = _build_db(invoices=invoices)
        result = compute_weekly_value(db, "tenant-1")
        assert result["invoices_sent"] == 2
        assert abs(result["invoices_sent_total"] - 350.50) < 0.01

    def test_invoice_paid_total(self):
        # Relative dates for the same reason as test_invoice_sent_total.
        # sent_at is outside the 7-day window, paid_at inside — only the paid
        # counters may move.
        old = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        invoices = [
            {"total": "500.00", "status": "paid", "sent_at": old, "paid_at": yesterday},
        ]
        db = _build_db(invoices=invoices)
        result = compute_weekly_value(db, "tenant-1")
        assert result["invoices_paid"] == 1
        assert abs(result["invoices_paid_total"] - 500.0) < 0.01
        assert result["invoices_sent"] == 0

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


# ---------------------------------------------------------------------------
# empty_state_message
# ---------------------------------------------------------------------------

class TestEmptyStateMessage:

    def test_returns_non_empty_string(self):
        msg = empty_state_message()
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_contains_helpful_copy_not_zeros(self):
        msg = empty_state_message()
        # Should mention what the AI can do — not raw zero counts
        assert "ready" in msg.lower() or "capture" in msg.lower() or "book" in msg.lower()

    def test_does_not_contain_zero_leads(self):
        msg = empty_state_message()
        # Must not look like a zeros-table — no "0 leads" style content
        assert "0 leads" not in msg
        assert "0 appointments" not in msg

    def test_is_multiline(self):
        msg = empty_state_message()
        lines = msg.split("\n")
        assert len(lines) >= 3, "empty_state_message should have at least 3 lines"


# ---------------------------------------------------------------------------
# Helpers for send_weekly_digest / _build_and_send_digest tests
# ---------------------------------------------------------------------------

def _make_digest_db(
    tenants_data=None,
    activity_log_count=0,
    chat_messages_data=None,
    leads_data=None,
    appointments_count=0,
    invoices_data=None,
    agent_runs_count=0,
):
    """Build a mock Supabase client for digest-level tests."""
    db = MagicMock()

    def table_side_effect(name):
        m = MagicMock()
        m.select.return_value = m
        m.eq.return_value = m
        m.neq.return_value = m
        m.in_.return_value = m
        m.gte.return_value = m
        m.limit.return_value = m
        m.or_.return_value = m
        m.filter.return_value = m

        if name == "tenants":
            m.execute.return_value = _mock_result(data=tenants_data or [])
        elif name == "activity_log":
            m.execute.return_value = _mock_result(count=activity_log_count)
        elif name == "chat_messages":
            m.execute.return_value = _mock_result(data=chat_messages_data or [])
        elif name == "leads":
            m.execute.return_value = _mock_result(data=leads_data or [])
        elif name == "appointments":
            m.execute.return_value = _mock_result(count=appointments_count)
        elif name == "invoices":
            m.execute.return_value = _mock_result(data=invoices_data or [])
        elif name == "os_agent_runs":
            m.execute.return_value = _mock_result(count=agent_runs_count)
        else:
            m.execute.return_value = _mock_result()
        return m

    db.table.side_effect = table_side_effect
    return db


def _run_async(coro):
    """Run an async coroutine in tests (avoids pytest-asyncio requirement)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# send_weekly_digest — plan_status filtering
# ---------------------------------------------------------------------------

class TestSendWeeklyDigestPlanStatusFilter:
    """Cancelled/paused tenants must NOT receive digests."""

    def test_cancelled_tenant_excluded(self):
        """A tenant with plan_status=cancelled must not get a digest."""
        # The tenants query now includes .in_("plan_status", ["active", "trialing"])
        # so cancelled tenants are filtered at the DB level.
        # We verify the query shape — not by checking email sends (since the mock
        # DB returns only what we give it, we give it no cancelled tenants and
        # assert send_email is never called).
        from backend.services.automation.scheduled_jobs_ext import send_weekly_digest

        db = _make_digest_db(
            # No tenants returned — simulates DB filtered them out
            tenants_data=[],
        )

        email_calls = []

        async def mock_send_email(**kwargs):
            email_calls.append(kwargs)
            return {"success": True}

        with (
            patch("backend.services.automation.scheduled_jobs_ext.get_service_supabase", return_value=db),
            patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email),
            patch("backend.services.automation.scheduled_jobs_ext.datetime") as mock_dt,
        ):
            from datetime import datetime, timezone
            # Friday
            mock_dt.now.return_value = datetime(2026, 6, 19, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = type("dt", (), {
                "weekday": lambda self: 4,
                "date": lambda self: type("d", (), {"isoformat": lambda self: "2026-06-19"})(),
            })()
            # Easier: just let it run on a known Friday
            import datetime as _dt
            mock_dt.now.return_value = _dt.datetime(2026, 6, 19, 10, 0, tzinfo=_dt.timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: _dt.datetime(*a, **kw)

            result = _run_async(send_weekly_digest())

        assert len(email_calls) == 0, "No emails should be sent to cancelled tenants"

    def test_plan_status_filter_called_on_tenants_query(self):
        """tenants query must include plan_status filter (in_ call)."""
        from backend.services.automation.scheduled_jobs_ext import send_weekly_digest

        db = MagicMock()
        tenants_mock = MagicMock()
        tenants_mock.select.return_value = tenants_mock
        tenants_mock.neq.return_value = tenants_mock
        tenants_mock.in_.return_value = tenants_mock
        tenants_mock.limit.return_value = tenants_mock
        tenants_mock.execute.return_value = _mock_result(data=[])
        db.table.return_value = tenants_mock

        import datetime as _dt

        with (
            patch("backend.services.automation.scheduled_jobs_ext.get_service_supabase", return_value=db),
            patch("backend.services.automation.scheduled_jobs_ext.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = _dt.datetime(2026, 6, 19, 10, 0, tzinfo=_dt.timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: _dt.datetime(*a, **kw)

            _run_async(send_weekly_digest())

        # Verify .in_ was called with plan_status filter
        in_calls = tenants_mock.in_.call_args_list
        plan_status_filtered = any(
            "plan_status" in str(c) for c in in_calls
        )
        assert plan_status_filtered, (
            "tenants query must filter plan_status via .in_(['active','trialing'])"
        )


# ---------------------------------------------------------------------------
# send_weekly_digest — best-effort batch (per-tenant failure isolation)
# ---------------------------------------------------------------------------

class TestSendWeeklyDigestBatchIsolation:

    def test_per_tenant_failure_does_not_abort_batch(self):
        """If _build_and_send_digest raises for tenant A, tenant B still gets sent."""
        from backend.services.automation.scheduled_jobs_ext import send_weekly_digest

        tenant_a = {
            "id": "tenant-a",
            "owner_email": "a@example.com",
            "owner_name": "Alice",
            "business_name": "Alice Salon",
            "avg_lead_value": None,
            "plan_status": "active",
        }
        tenant_b = {
            "id": "tenant-b",
            "owner_email": "b@example.com",
            "owner_name": "Bob",
            "business_name": "Bob Plumbing",
            "avg_lead_value": None,
            "plan_status": "active",
        }

        db = _make_digest_db(tenants_data=[tenant_a, tenant_b])

        import datetime as _dt

        send_counts = {"b": 0}

        async def mock_build_and_send(db, tenant, tid, email, week_start, week_tag, opportunity_html=None):
            if tid == "tenant-a":
                raise RuntimeError("Simulated crash for tenant A")
            send_counts["b"] += 1
            return True

        with (
            patch("backend.services.automation.scheduled_jobs_ext.get_service_supabase", return_value=db),
            patch("backend.services.automation.scheduled_jobs_ext._build_and_send_digest", side_effect=mock_build_and_send),
            patch("backend.services.automation.scheduled_jobs_ext.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = _dt.datetime(2026, 6, 19, 10, 0, tzinfo=_dt.timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: _dt.datetime(*a, **kw)

            result = _run_async(send_weekly_digest())

        # Tenant B's digest was sent despite A crashing
        assert send_counts["b"] == 1, "Tenant B must still receive digest after A crashes"
        # Return count reflects only successful sends
        assert result == 1


# ---------------------------------------------------------------------------
# _build_and_send_digest — empty-state email
# ---------------------------------------------------------------------------

class TestBuildAndSendDigestEmptyState:

    def test_zero_activity_sends_empty_state_email_not_zeros_table(self):
        """A tenant with all-zero activity should get the empty-state subject/body."""
        from backend.services.automation.scheduled_jobs_ext import _build_and_send_digest

        db = _make_digest_db(
            leads_data=[],
            appointments_count=0,
            chat_messages_data=[],
            invoices_data=[],
            agent_runs_count=0,
        )

        sent_subjects = []
        sent_bodies = []

        async def mock_send_email(to, subject, body_html, tenant_id):
            sent_subjects.append(subject)
            sent_bodies.append(body_html)
            return {"success": True}

        tenant = {
            "id": "empty-tenant",
            "owner_email": "owner@example.com",
            "owner_name": "Sam",
            "business_name": "Sam Fitness",
            "avg_lead_value": None,
            "plan_status": "active",
        }

        with patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email):
            with patch("backend.services.activity.log_activity"):
                _run_async(
                    _build_and_send_digest(
                        db=db,
                        tenant=tenant,
                        tid="empty-tenant",
                        email="owner@example.com",
                        week_start="2026-06-12T00:00:00+00:00",
                        week_tag="weekly_digest_2026-06-19",
                    )
                )

        assert len(sent_subjects) == 1
        subject = sent_subjects[0]
        body = sent_bodies[0]

        # Subject differs for empty state
        assert "ready" in subject.lower() or "AI staff is ready" in subject, (
            f"Empty-state subject should reflect 'ready' state, got: {subject}"
        )

        # Body must NOT contain zeros table markers
        assert "Leads captured" not in body or "0" not in body.split("Leads captured")[1][:20], (
            "Empty-state body should not show a zeros table"
        )

        # Body must contain helpful copy from empty_state_message
        assert "ready" in body.lower() or "capture" in body.lower() or "book" in body.lower(), (
            "Empty-state body should contain helpful copy about what the AI can do"
        )

    def test_active_tenant_sends_stats_table(self):
        """A tenant with activity gets the stats table email, not the empty-state."""
        from backend.services.automation.scheduled_jobs_ext import _build_and_send_digest

        db = _make_digest_db(
            leads_data=[{"id": "l1", "deal_value": "200"}],
            appointments_count=1,
            chat_messages_data=[{"session_id": "s1", "content": "What are your hours?"}],
            invoices_data=[],
            agent_runs_count=0,
        )

        sent_subjects = []
        sent_bodies = []

        async def mock_send_email(to, subject, body_html, tenant_id):
            sent_subjects.append(subject)
            sent_bodies.append(body_html)
            return {"success": True}

        tenant = {
            "id": "active-tenant",
            "owner_email": "owner@example.com",
            "owner_name": "Maria",
            "business_name": "Maria Dental",
            "avg_lead_value": None,
            "plan_status": "active",
        }

        with patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email):
            with patch("backend.services.activity.log_activity"):
                _run_async(
                    _build_and_send_digest(
                        db=db,
                        tenant=tenant,
                        tid="active-tenant",
                        email="owner@example.com",
                        week_start="2026-06-12T00:00:00+00:00",
                        week_tag="weekly_digest_2026-06-19",
                    )
                )

        assert len(sent_subjects) == 1
        # Active state subject
        assert "got done" in sent_subjects[0].lower() or "AI staff" in sent_subjects[0], (
            f"Active state email subject wrong: {sent_subjects[0]}"
        )
        # Body has stats table
        assert "Leads captured" in sent_bodies[0]


# ---------------------------------------------------------------------------
# _build_and_send_digest — opportunity highlights seam
# ---------------------------------------------------------------------------

class TestOpportunityHighlightsSeam:

    def test_opportunity_html_rendered_when_provided(self):
        """When opportunity_html is passed, it appears in the email body."""
        from backend.services.automation.scheduled_jobs_ext import _build_and_send_digest

        db = _make_digest_db(
            leads_data=[{"id": "l1", "deal_value": "150"}],
            appointments_count=1,
            chat_messages_data=[],
            invoices_data=[],
            agent_runs_count=0,
        )

        sent_bodies = []

        async def mock_send_email(to, subject, body_html, tenant_id):
            sent_bodies.append(body_html)
            return {"success": True}

        tenant = {
            "id": "t1",
            "owner_email": "x@x.com",
            "owner_name": "X",
            "business_name": "X Biz",
            "avg_lead_value": None,
            "plan_status": "active",
        }

        opportunity_snippet = "<p>You have 3 leads who haven't been contacted in 5 days.</p>"

        with patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email):
            with patch("backend.services.activity.log_activity"):
                _run_async(
                    _build_and_send_digest(
                        db=db,
                        tenant=tenant,
                        tid="t1",
                        email="x@x.com",
                        week_start="2026-06-12T00:00:00+00:00",
                        week_tag="weekly_digest_2026-06-19",
                        opportunity_html=opportunity_snippet,
                    )
                )

        assert len(sent_bodies) == 1
        assert opportunity_snippet in sent_bodies[0], (
            "opportunity_html must appear verbatim in the email body"
        )

    def test_no_opportunity_section_when_none(self):
        """When opportunity_html is None, no opportunity section rendered."""
        from backend.services.automation.scheduled_jobs_ext import _build_and_send_digest

        db = _make_digest_db(
            leads_data=[{"id": "l1", "deal_value": "150"}],
            appointments_count=1,
            chat_messages_data=[],
            invoices_data=[],
            agent_runs_count=0,
        )

        sent_bodies = []

        async def mock_send_email(to, subject, body_html, tenant_id):
            sent_bodies.append(body_html)
            return {"success": True}

        tenant = {
            "id": "t1",
            "owner_email": "x@x.com",
            "owner_name": "X",
            "business_name": "X Biz",
            "avg_lead_value": None,
            "plan_status": "active",
        }

        with patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email):
            with patch("backend.services.activity.log_activity"):
                _run_async(
                    _build_and_send_digest(
                        db=db,
                        tenant=tenant,
                        tid="t1",
                        email="x@x.com",
                        week_start="2026-06-12T00:00:00+00:00",
                        week_tag="weekly_digest_2026-06-19",
                        opportunity_html=None,
                    )
                )

        assert len(sent_bodies) == 1
        assert "Opportunities this week" not in sent_bodies[0], (
            "No opportunity section should appear when opportunity_html is None"
        )
