"""Round-5 contracts: signed email approve/reject links, stage-2 plan gate,
legacy token baselines, fast-path instrumentation, project step enrichment."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.services import os_email_actions


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Result:
    def __init__(self, data, count=0):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, rows, sink, table):
        self._rows = rows
        self._sink = sink
        self._table = table

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((self._table, name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows_by_table, sink=None):
    sink = sink if sink is not None else []
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(
        rows_by_table.get(name, []), sink, name
    )
    db._sink = sink
    return db


_SECRET = patch(
    "backend.services.os_email_actions._secret", return_value=b"test-secret"
)


# --- token make/verify ------------------------------------------------------


class TestEmailActionTokens:
    def test_round_trip(self):
        with _SECRET:
            token = os_email_actions.make_action_token("c1", "r1", "approve")
            payload = os_email_actions.verify_action_token(token)
        assert payload == {
            "c": "c1",
            "r": "r1",
            "a": "approve",
            "e": payload["e"],
        }
        assert payload["e"] > time.time()

    def test_tampered_signature_rejected(self):
        with _SECRET:
            token = os_email_actions.make_action_token("c1", "r1", "approve")
            bad = token[:-4] + ("0000" if not token.endswith("0000") else "1111")
            assert os_email_actions.verify_action_token(bad) is None

    def test_token_for_other_action_not_interchangeable(self):
        with _SECRET:
            approve = os_email_actions.make_action_token("c1", "r1", "approve")
            reject = os_email_actions.make_action_token("c1", "r1", "reject")
        assert approve != reject

    def test_expired_token_rejected(self):
        with _SECRET:
            token = os_email_actions.make_action_token("c1", "r1", "approve")
            with patch(
                "backend.services.os_email_actions.time.time",
                return_value=time.time()
                + os_email_actions.TOKEN_TTL_SECONDS
                + 60,
            ):
                assert os_email_actions.verify_action_token(token) is None

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError):
            os_email_actions.make_action_token("c1", "r1", "delete")

    def test_garbage_tokens_rejected(self):
        with _SECRET:
            for garbage in ("", "abc", "a.b", "notbase64.deadbeef"):
                assert os_email_actions.verify_action_token(garbage) is None

    def test_missing_secret_rejects_everything(self):
        with _SECRET:
            token = os_email_actions.make_action_token("c1", "r1", "approve")
        with patch(
            "backend.services.os_email_actions._secret", return_value=b""
        ):
            assert os_email_actions.verify_action_token(token) is None


# --- apply_action -----------------------------------------------------------


_PENDING_RUN = {
    "id": "r1",
    "deliverable": {"title": "Welcome email"},
    "deliverable_status": "pending_approval",
    "action_type": "email.send",
}


class TestApplyAction:
    def test_approve_queues_action_and_marks_approved(self):
        sink: list = []
        db = _db({"os_agent_runs": [_PENDING_RUN]}, sink)
        payload = {"c": "c1", "r": "r1", "a": "approve"}
        with patch(
            "backend.services.os_action_dispatch.queue_action_for_run",
            new=AsyncMock(return_value="ar1"),
        ) as queue, patch("backend.services.activity.log_activity"):
            state, title = _run(os_email_actions.apply_action(db, payload))
        assert state == "done" and title == "Welcome email"
        queue.assert_awaited_once()
        updates = [s for s in sink if s[0] == "os_agent_runs" and s[1] == "update"]
        assert updates[0][2][0]["deliverable_status"] == "approved"
        assert updates[0][2][0]["action_run_id"] == "ar1"

    def test_reject_marks_rejected_without_queueing(self):
        sink: list = []
        db = _db({"os_agent_runs": [_PENDING_RUN]}, sink)
        payload = {"c": "c1", "r": "r1", "a": "reject"}
        with patch(
            "backend.services.os_action_dispatch.queue_action_for_run",
            new=AsyncMock(),
        ) as queue, patch("backend.services.activity.log_activity"):
            state, _ = _run(os_email_actions.apply_action(db, payload))
        assert state == "done"
        queue.assert_not_awaited()
        updates = [s for s in sink if s[0] == "os_agent_runs" and s[1] == "update"]
        assert updates[0][2][0]["deliverable_status"] == "rejected"

    def test_already_decided_run_reports_state_without_refiring(self):
        run = {**_PENDING_RUN, "deliverable_status": "approved"}
        sink: list = []
        db = _db({"os_agent_runs": [run]}, sink)
        with patch(
            "backend.services.os_action_dispatch.queue_action_for_run",
            new=AsyncMock(),
        ) as queue:
            state, _ = _run(
                os_email_actions.apply_action(
                    db, {"c": "c1", "r": "r1", "a": "approve"}
                )
            )
        assert state == "already:approved"
        queue.assert_not_awaited()
        assert not [s for s in sink if s[1] == "update"]

    def test_missing_run_not_found(self):
        db = _db({"os_agent_runs": []})
        state, title = _run(
            os_email_actions.apply_action(db, {"c": "c1", "r": "r1", "a": "approve"})
        )
        assert state == "not_found" and title is None


# --- email-action pages (public, token-authed) ------------------------------


class TestEmailActionRouter:
    def _client(self):
        from backend.main import app
        from backend.tests.conftest import SyncASGITestClient

        return SyncASGITestClient(app)

    def test_invalid_token_renders_expired_page(self):
        resp = self._client().get(
            "/api/v1/os/deliverables/email-action?token=not-a-real-token"
        )
        assert resp.status_code == 200
        assert "no longer valid" in resp.text

    def test_get_renders_confirmation_not_mutation(self):
        payload = {"c": "c1", "r": "r1", "a": "approve", "e": 9999999999}
        with patch(
            "backend.routers.os_email_actions.verify_action_token",
            return_value=payload,
        ), patch(
            "backend.routers.os_email_actions.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_email_actions.load_pending_title",
            return_value=("pending", "Welcome email"),
        ), patch(
            "backend.routers.os_email_actions.apply_action",
            new=AsyncMock(),
        ) as apply:
            resp = self._client().get(
                "/api/v1/os/deliverables/email-action?token=" + "x" * 32
            )
        assert resp.status_code == 200
        assert "Approve this draft?" in resp.text
        assert "Welcome email" in resp.text
        apply.assert_not_awaited()

    def test_post_applies_the_action(self):
        payload = {"c": "c1", "r": "r1", "a": "approve", "e": 9999999999}
        with patch(
            "backend.routers.os_email_actions.verify_action_token",
            return_value=payload,
        ), patch(
            "backend.routers.os_email_actions.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_email_actions.apply_action",
            new=AsyncMock(return_value=("done", "Welcome email")),
        ) as apply:
            resp = self._client().post(
                "/api/v1/os/deliverables/email-action?token=" + "x" * 32
            )
        assert resp.status_code == 200
        assert "approved" in resp.text
        apply.assert_awaited_once()

    def test_already_handled_page(self):
        payload = {"c": "c1", "r": "r1", "a": "reject", "e": 9999999999}
        with patch(
            "backend.routers.os_email_actions.verify_action_token",
            return_value=payload,
        ), patch(
            "backend.routers.os_email_actions.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_email_actions.apply_action",
            new=AsyncMock(return_value=("already:rejected", "T")),
        ):
            resp = self._client().post(
                "/api/v1/os/deliverables/email-action?token=" + "x" * 32
            )
        assert "Already rejected" in resp.text


# --- rollup email carries per-draft action links ----------------------------


class TestRollupDraftLinks:
    def test_draft_rows_include_signed_links(self):
        from backend.services.os_approval_rollup import _draft_rows_html

        with _SECRET:
            html = _draft_rows_html(
                "c1", [{"id": "r1", "title": "Welcome <email>"}]
            )
        assert "email-action?token=" in html
        assert "Approve" in html and "Reject" in html
        # Title is escaped, never raw HTML.
        assert "<email>" not in html
        assert "Welcome &lt;email&gt;" in html

    def test_no_drafts_no_rows(self):
        from backend.services.os_approval_rollup import _draft_rows_html

        assert _draft_rows_html("c1", []) == ""

    def test_rollup_email_body_contains_action_links(self):
        from backend.services import os_approval_rollup

        old = "2020-01-01T00:00:00+00:00"
        db = _db(
            {
                "os_agent_runs": [
                    {
                        "id": "r1",
                        "client_id": "c1",
                        "created_at": old,
                        "deliverable": {"title": "Welcome email"},
                    }
                ],
                "activity_log": [],
                "tenants": [
                    {
                        "business_name": "Biz",
                        "owner_email": "o@x.com",
                        "owner_name": "Sam",
                    }
                ],
            }
        )
        send = AsyncMock(return_value={"success": True})
        with _SECRET, patch(
            "backend.models.database.get_service_supabase", return_value=db
        ), patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.email_sender.send_email", new=send
        ), patch(
            "backend.services.email_sender.mask_email", return_value="o***"
        ), patch(
            "backend.services.activity.log_activity"
        ):
            sent = _run(os_approval_rollup.send_approval_rollups())
        assert sent == 1
        body = send.await_args.kwargs["body_html"]
        assert "email-action?token=" in body
        assert "Welcome email" in body


# --- stage-2 plan gate on core chat routers ---------------------------------


class TestStage2Gate:
    def _gated(self, router) -> bool:
        from backend.services.agent_os_gate import require_agent_os_access

        return any(
            getattr(dep, "dependency", None) is require_agent_os_access
            for dep in (router.dependencies or [])
        )

    def test_core_chat_routers_are_gated(self):
        from backend.routers import os_deliverables, os_orchestrate, os_threads

        assert self._gated(os_threads.router)
        assert self._gated(os_orchestrate.router)
        assert self._gated(os_deliverables.router)

    def test_email_action_router_stays_public(self):
        from backend.routers import os_email_actions as email_router

        assert not self._gated(email_router.router)

    def test_demo_plan_is_inside_the_gate(self):
        # The public demo sandbox runs on 'professional' demo tenants - the
        # stage-2 gate must never 402 the demo.
        from backend.services.agent_os_gate import AGENT_OS_PLANS

        assert "professional" in AGENT_OS_PLANS


# --- legacy plan token baselines --------------------------------------------


class TestLegacyBaselines:
    def test_every_known_plan_has_an_enforced_baseline(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        from backend.services.plan_catalog import ALL_KNOWN_PLANS

        for plan in ALL_KNOWN_PLANS:
            assert plan in PLAN_BASELINE_TOKENS, (
                f"{plan} would silently fall to the chatbot default"
            )

    def test_legacy_baselines_match_reconciliation_mirror(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        from backend.services.billing_reconciliation import (
            _PLAN_BASELINE_AI_TOKENS,
        )
        from backend.services.plan_catalog import LEGACY_PAID_PLANS

        for plan in LEGACY_PAID_PLANS:
            assert PLAN_BASELINE_TOKENS[plan] == _PLAN_BASELINE_AI_TOKENS[plan]

    def test_current_tier_values_unchanged(self):
        # Re-baseline measurement 2026-07-22: heaviest tenant-month is 363k
        # tokens - current tiers keep headroom and must not drift silently.
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS

        assert PLAN_BASELINE_TOKENS["chatbot"] == 800_000
        assert PLAN_BASELINE_TOKENS["agent_os"] == 5_000_000


# --- fast-path instrumentation ----------------------------------------------


class TestFastPathInstrumentation:
    def test_data_answer_logs_usage(self):
        from backend.services import os_data_answers

        db = _db(
            {"os_messages": [{"id": "m2", "content": "x"}], "os_threads": []}
        )
        with patch(
            "backend.services.biz_answers.match_template", return_value="leads"
        ), patch(
            "backend.services.biz_answers.answer_question",
            return_value={"matched": True, "answer": "4 leads", "template": "leads"},
        ), patch(
            "backend.services.activity.log_activity"
        ) as log:
            out = _run(
                os_data_answers.try_data_answer(
                    db, "c1", "th1", {"content": "how many leads this week?"}
                )
            )
        assert out is not None
        assert (
            log.call_args.kwargs["activity_type"] == "os_fast_path_data_answer"
        )

    def test_chat_project_logs_usage(self):
        from backend.services import os_chat_projects

        db = _db(
            {
                "os_threads": [{"id": "th1", "source": "chat"}],
                "tenants": [{"plan": "agent_os"}],
                "os_projects": [{"id": "p1", "status": "planning"}],
                "os_messages": [{"id": "m2", "content": "reply"}],
            }
        )
        with patch(
            "backend.services.platform_flags.flag_enabled", return_value=True
        ), patch("backend.services.activity.log_activity") as log:
            out = _run(
                os_chat_projects.try_start_project(
                    db,
                    "c1",
                    "th1",
                    {"id": "m1", "content": "start a project: launch a promo"},
                )
            )
        assert out is not None and out.get("project")
        assert (
            log.call_args.kwargs["activity_type"] == "os_fast_path_chat_project"
        )

    def test_research_logs_usage(self):
        from backend.services import os_research

        db = _db({"os_agent_runs": [{"id": "run1"}]})
        result = MagicMock()
        result.text = "Brief text"
        with patch(
            "backend.services.os_research.gather_sources",
            new=AsyncMock(return_value=("corpus", ["knowledge base"])),
        ), patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=result),
        ), patch(
            "backend.services.activity.log_activity"
        ) as log:
            out = _run(
                os_research.run_research(db, "c1", "pricing strategy research")
            )
        assert out.get("run")
        assert log.call_args.kwargs["activity_type"] == "os_research_run"

    def test_loop_health_fast_paths_section(self):
        from backend.routers.admin_loop_health import _fast_paths_section
        from datetime import datetime, timezone

        db = _db(
            {
                "activity_log": [
                    {"activity_type": "os_fast_path_data_answer"},
                    {"activity_type": "os_fast_path_data_answer"},
                    {"activity_type": "email_action_approve"},
                ]
            }
        )
        out = _fast_paths_section(db, datetime.now(timezone.utc))
        assert out["os_fast_path_data_answer"] == 2
        assert out["email_action_approve"] == 1
        assert out["os_fast_path_chat_project"] == 0

    def test_loop_health_fast_paths_failure_returns_none(self):
        from backend.routers.admin_loop_health import _fast_paths_section
        from datetime import datetime, timezone

        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert _fast_paths_section(db, datetime.now(timezone.utc)) is None


# --- project step enrichment -------------------------------------------------


class TestProjectStepEnrichment:
    def test_steps_gain_deliverable_status_and_title(self):
        from backend.routers.os_projects import _attach_deliverables

        steps = [
            {"id": "s1", "agent_run_id": "r1", "status": "awaiting_approval"},
            {"id": "s2", "status": "pending"},
        ]
        db = _db(
            {
                "os_agent_runs": [
                    {
                        "id": "r1",
                        "deliverable": {"title": "Promo email"},
                        "deliverable_status": "pending_approval",
                    }
                ]
            }
        )
        out = _attach_deliverables(db, "c1", steps)
        assert out[0]["deliverable_status"] == "pending_approval"
        assert out[0]["deliverable_title"] == "Promo email"
        assert "deliverable_status" not in out[1]

    def test_no_runs_returns_steps_unchanged(self):
        from backend.routers.os_projects import _attach_deliverables

        steps = [{"id": "s1", "status": "pending"}]
        db = MagicMock()
        assert _attach_deliverables(db, "c1", steps) == steps
        db.table.assert_not_called()

    def test_db_failure_returns_bare_steps(self):
        from backend.routers.os_projects import _attach_deliverables

        steps = [{"id": "s1", "agent_run_id": "r1"}]
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert _attach_deliverables(db, "c1", steps) == steps
