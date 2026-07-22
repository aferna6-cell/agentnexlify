"""Round-8 contracts: approval-queue dedupe at generation, nameless-lead
title fallback, one-click view meter, and the decision-funnel loop-health
section."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("TESTING", "1")

from backend.services import os_opportunity_fulfill as fulfill

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


class _Query:
    def __init__(self, rows):
        self._rows = rows
        self.inserted_rows = []

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            return self

        return chain

    def insert(self, row):
        self.inserted_rows.append(row)
        self._rows = [dict(row, id="new-1")]
        return self

    def execute(self):
        return MagicMock(data=self._rows)


def _lead(n, name="Lead {n}", email="", phone=""):
    return {
        "id": f"lead-{n}",
        "name": name.format(n=n),
        "email": email,
        "phone": phone,
        "areas_of_interest": "",
    }


def _run_followups(leads, pending_rows):
    """Drive _draft_lead_followups with fixture leads + pending drafts."""
    inserts = []

    def tenant_table(db, table, client_id):
        if table == "leads":
            return _Query(list(leads))
        if table == "os_agent_runs":
            q = _Query(list(pending_rows))
            orig_insert = q.insert

            def record_insert(row):
                inserts.append(row)
                return orig_insert(row)

            q.insert = record_insert
            return q
        if table == "tenants":
            return _Query([{"business_name": "Acme", "owner_name": "Sam"}])
        return _Query([])

    with (
        patch.object(fulfill, "tenant_table", tenant_table),
        patch.object(
            fulfill.os_approval_notify, "notify_pending_approval", AsyncMock()
        ),
    ):
        n = asyncio.run(fulfill._draft_lead_followups(MagicMock(), _TENANT))
    return n, inserts


class TestDedupeAtGeneration:
    def test_lead_with_pending_draft_is_skipped(self):
        # Prod 2026-07-22: 5 identical "Check in with Amy" drafts in one
        # day - re-accepting the suggestion re-drafted every cold lead.
        pending = [
            {"deliverable": {"metadata": {"lead_id": "lead-1"}}},
        ]
        leads = [_lead(1, email="amy@x.com"), _lead(2, email="bob@x.com")]
        n, inserts = _run_followups(leads, pending)
        assert n == 1
        drafted_leads = [
            i["deliverable"]["metadata"]["lead_id"] for i in inserts
        ]
        assert drafted_leads == ["lead-2"]

    def test_no_pending_drafts_means_all_contactable_drafted(self):
        leads = [_lead(1, email="amy@x.com"), _lead(2, email="bob@x.com")]
        n, _ = _run_followups(leads, [])
        assert n == 2

    def test_pending_scan_failure_fails_open(self):
        # A scan blip must not block fulfillment entirely.
        def tenant_table(db, table, client_id):
            raise RuntimeError("db down")

        with patch.object(fulfill, "tenant_table", tenant_table):
            assert fulfill._pending_metadata_ids(MagicMock(), _TENANT, "lead_id") == set()


class TestNamelessLeadTitle:
    def test_title_falls_back_to_recipient_not_there(self):
        # "Check in with there" shipped to real queues when name was empty.
        leads = [_lead(1, name="", email="mystery@x.com")]
        n, inserts = _run_followups(leads, [])
        assert n == 1
        assert inserts[0]["deliverable"]["title"] == "Check in with mystery@x.com"

    def test_named_lead_keeps_name_in_title(self):
        leads = [_lead(1, name="Amanda Smith", email="a@x.com")]
        _, inserts = _run_followups(leads, [])
        assert inserts[0]["deliverable"]["title"] == "Check in with Amanda Smith"


class TestEmailActionViewMeter:
    def _get(self, payload, state="pending", title="Welcome email"):
        from backend.main import app
        from backend.tests.conftest import SyncASGITestClient

        log = MagicMock()
        with patch(
            "backend.routers.os_email_actions.verify_action_token",
            return_value=payload,
        ), patch(
            "backend.routers.os_email_actions.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_email_actions.load_pending_title",
            return_value=(state, title),
        ), patch(
            "backend.services.activity.log_activity", log
        ):
            resp = SyncASGITestClient(app).get(
                "/api/v1/os/deliverables/email-action?token=" + "x" * 32
            )
        return resp, log

    def test_valid_token_get_logs_view(self):
        payload = {"c": "c1", "r": "r1", "a": "approve", "e": 9999999999}
        resp, log = self._get(payload)
        assert resp.status_code == 200
        assert "Approve this draft?" in resp.text
        kwargs = log.call_args.kwargs
        assert kwargs["activity_type"] == "email_action_viewed"
        assert kwargs["tenant_id"] == "c1"
        assert kwargs["metadata"]["run_id"] == "r1"

    def test_invalid_token_logs_nothing(self):
        from backend.main import app
        from backend.tests.conftest import SyncASGITestClient

        log = MagicMock()
        with patch("backend.services.activity.log_activity", log):
            resp = SyncASGITestClient(app).get(
                "/api/v1/os/deliverables/email-action?token=not-a-real-token"
            )
        assert resp.status_code == 200
        assert "no longer valid" in resp.text
        log.assert_not_called()


class TestDecisionFunnelSection:
    def test_counts_and_median_latency(self):
        from backend.routers.admin_loop_health import _decision_funnel_section

        now = datetime.now(timezone.utc)
        created = (now - timedelta(hours=10)).isoformat()
        decided_rows = [
            {
                "created_at": created,
                "updated_at": (now - timedelta(hours=4)).isoformat(),
                "deliverable_status": "approved",
            },
            {
                "created_at": created,
                "updated_at": (now - timedelta(hours=8)).isoformat(),
                "deliverable_status": "rejected",
            },
        ]

        pending_result = MagicMock()
        pending_result.count = 39

        db = MagicMock()

        def table(name):
            chain = MagicMock()
            (
                chain.select.return_value.eq.return_value.limit.return_value
                .execute.return_value
            ) = pending_result
            (
                chain.select.return_value.in_.return_value.gte.return_value
                .limit.return_value.execute.return_value
            ) = MagicMock(data=decided_rows)
            return chain

        db.table.side_effect = table
        out = _decision_funnel_section(db, now)
        assert out["pending_now"] == 39
        assert out["decided_7d"] == 2
        assert out["approved_7d"] == 1
        assert out["rejected_7d"] == 1
        # Latencies 6h and 2h -> sorted [2, 6], median index 1 -> 6.0
        assert out["median_decision_hours"] == 6.0

    def test_query_failure_returns_none(self):
        from backend.routers.admin_loop_health import _decision_funnel_section

        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert _decision_funnel_section(db, datetime.now(timezone.utc)) is None

    def test_viewed_meter_in_fast_path_types(self):
        from backend.routers.admin_loop_health import _FAST_PATH_TYPES

        assert "email_action_viewed" in _FAST_PATH_TYPES
