"""Round-3 contracts: suite plan gate, chat data answers, runner-planned
projects, research v1, approval rollup."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.services import (
    agent_os_gate,
    os_approval_rollup,
    os_data_answers,
    os_projects,
    os_research,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Result:
    def __init__(self, data, count=None):
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


CLAIMS = {"tenant_id": "t1"}


class TestAgentOsGate:
    def _gate(self, plan_rows):
        with patch(
            "backend.services.agent_os_gate.get_service_supabase",
            return_value=_db({"tenants": plan_rows}),
        ):
            return _run(agent_os_gate.require_agent_os_access(CLAIMS))

    def test_agent_os_plan_passes(self):
        assert self._gate([{"plan": "agent_os"}]) == CLAIMS

    def test_legacy_plans_grandfathered(self):
        for plan in ("growth", "autopilot", "professional", "enterprise"):
            assert self._gate([{"plan": plan}]) == CLAIMS

    def test_chatbot_plan_402_with_upgrade_payload(self):
        with pytest.raises(HTTPException) as err:
            self._gate([{"plan": "chatbot"}])
        assert err.value.status_code == 402
        assert err.value.detail["required_plan"] == "agent_os"
        assert err.value.detail["upgrade_path"] == "/billing"

    def test_free_plan_402(self):
        with pytest.raises(HTTPException):
            self._gate([{"plan": "free"}])

    def test_db_failure_fails_open(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        with patch(
            "backend.services.agent_os_gate.get_service_supabase", return_value=db
        ):
            assert _run(agent_os_gate.require_agent_os_access(CLAIMS)) == CLAIMS

    def test_missing_tenant_id_401(self):
        with pytest.raises(HTTPException) as err:
            _run(agent_os_gate.require_agent_os_access({}))
        assert err.value.status_code == 401


class TestChatDataAnswers:
    _MSG = {"content": "how many leads this week?"}

    def test_matched_question_answered_and_persisted(self):
        sink: list = []
        db = _db(
            {"leads": [{"id": "l1"}], "os_messages": [{"id": "m2", "content": "x"}]},
            sink,
        )
        out = _run(os_data_answers.try_data_answer(db, "c1", "th1", self._MSG))
        assert out is not None
        assert out["data_answer"] is True and out["action"] == "answer"
        inserts = [s for s in sink if s[0] == "os_messages" and s[1] == "insert"]
        assert "live business data" in str(inserts[0][2])

    def test_non_data_question_passes_through(self):
        db = _db({})
        msg = {"content": "write a poem about our cafe"}
        assert _run(os_data_answers.try_data_answer(db, "c1", "th1", msg)) is None

    def test_long_message_passes_through(self):
        db = _db({})
        msg = {"content": "lead " * 60}
        assert _run(os_data_answers.try_data_answer(db, "c1", "th1", msg)) is None

    def test_answer_error_passes_through_to_engine(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert (
            _run(os_data_answers.try_data_answer(db, "c1", "th1", self._MSG)) is None
        )


PLAN_TEXT = (
    '{"title": "Fall promo", "steps": ['
    '{"department": "marketing", "objective": "Draft the promo email"},'
    '{"department": "sales", "objective": "Draft warm-lead follow-ups"}]}'
)


class TestRunnerPlannedProjects:
    def test_plans_pending_projects_to_draft(self):
        sink: list = []
        project = {"id": "p1", "client_id": "c1", "ask": "launch fall promo",
                   "status": "planning"}
        db = _db({"os_projects": [project]}, sink)
        fake = MagicMock()
        fake.text = PLAN_TEXT
        with patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=fake),
        ):
            planned = _run(os_projects.plan_pending_projects(db))
        assert planned == 1
        step_inserts = [
            s for s in sink if s[0] == "os_project_steps" and s[1] == "insert"
        ]
        assert step_inserts and "marketing" in str(step_inserts[0][2])
        updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("draft" in str(u[2]) for u in updates)

    def test_planner_failure_leaves_errored_draft(self):
        sink: list = []
        project = {"id": "p1", "client_id": "c1", "ask": "launch fall promo",
                   "status": "planning"}
        db = _db({"os_projects": [project]}, sink)
        with patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(side_effect=RuntimeError("model down")),
        ):
            planned = _run(os_projects.plan_pending_projects(db))
        assert planned == 1
        updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("planner failed" in str(u[2]) for u in updates)

    def test_read_failure_returns_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert _run(os_projects.plan_pending_projects(db)) == 0

    def test_tick_runner_plans_before_advancing(self):
        db = _db({"os_projects": []})
        with patch.object(
            os_projects, "plan_pending_projects", new=AsyncMock()
        ) as plan:
            _run(os_projects.run_project_ticks(db))
        plan.assert_awaited_once()


class TestResearchV1:
    def test_short_topic_rejected(self):
        with pytest.raises(ValueError):
            _run(os_research.run_research(_db({}), "c1", "promo"))

    def test_empty_corpus_returns_helpful_error(self):
        with patch.object(
            os_research, "gather_sources", new=AsyncMock(return_value=("", []))
        ):
            out = _run(
                os_research.run_research(_db({}), "c1", "what do customers ask most?")
            )
        assert "No owned sources" in out["error"]

    def test_brief_parks_at_approval_gate_with_provenance(self):
        sink: list = []
        db = _db({"os_agent_runs": [{"id": "r1"}]}, sink)
        fake = MagicMock()
        fake.text = "Summary: customers ask about hours most."
        with patch.object(
            os_research,
            "gather_sources",
            new=AsyncMock(return_value=("[faq]\nhours 8-5", ["knowledge base"])),
        ), patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=fake),
        ):
            out = _run(
                os_research.run_research(db, "c1", "what do customers ask most?")
            )
        assert out["run"]["id"] == "r1"
        inserts = [s for s in sink if s[0] == "os_agent_runs" and s[1] == "insert"]
        row = inserts[0][2][0]
        assert row["deliverable_status"] == "pending_approval"
        assert "Sources drawn from: knowledge base" in row["deliverable"]["body"]

    def test_synthesis_failure_returns_error(self):
        with patch.object(
            os_research,
            "gather_sources",
            new=AsyncMock(return_value=("[faq]\nhours", ["knowledge base"])),
        ), patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(side_effect=RuntimeError("model down")),
        ):
            out = _run(
                os_research.run_research(_db({}), "c1", "what do customers ask most?")
            )
        assert "synthesis failed" in out["error"]


class TestApprovalRollup:
    _OLD = "2026-07-01T00:00:00+00:00"

    def _rollup_db(self, runs, dedupe_count=0, tenant_rows=None):
        sink: list = []

        def _table(name):
            if name == "os_agent_runs":
                return _Query(runs, sink, name)
            if name == "activity_log":
                chain = MagicMock()
                chain.select.return_value = chain
                chain.eq.return_value = chain
                chain.limit.return_value = chain
                chain.execute.return_value = _Result([], count=dedupe_count)
                return chain
            if name == "tenants":
                return _Query(
                    tenant_rows
                    if tenant_rows is not None
                    else [{"business_name": "B", "owner_email": "o@x.com",
                           "owner_name": "Sam"}],
                    sink,
                    name,
                )
            return _Query([], sink, name)

        db = MagicMock()
        db.table.side_effect = _table
        return db

    def test_stale_queue_gets_one_rollup(self):
        db = self._rollup_db([{"client_id": "c1", "created_at": self._OLD}] * 3)
        send = AsyncMock(return_value={"success": True})
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch("backend.services.email_sender.send_email", new=send), patch(
            "backend.services.activity.log_activity"
        ) as log:
            sent = _run(os_approval_rollup.send_approval_rollups())
        assert sent == 1
        assert "3 draft" in send.await_args.kwargs["subject"]
        log.assert_called_once()

    def test_young_queue_skipped(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        db = self._rollup_db([{"client_id": "c1", "created_at": now}])
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch("backend.services.email_sender.send_email", new=AsyncMock()) as send:
            assert _run(os_approval_rollup.send_approval_rollups()) == 0
        send.assert_not_awaited()

    def test_already_sent_today_deduped(self):
        db = self._rollup_db(
            [{"client_id": "c1", "created_at": self._OLD}], dedupe_count=1
        )
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch("backend.services.email_sender.send_email", new=AsyncMock()) as send:
            assert _run(os_approval_rollup.send_approval_rollups()) == 0
        send.assert_not_awaited()

    def test_no_owner_email_skipped(self):
        db = self._rollup_db(
            [{"client_id": "c1", "created_at": self._OLD}],
            tenant_rows=[{"business_name": "B", "owner_email": ""}],
        )
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch("backend.services.email_sender.send_email", new=AsyncMock()) as send:
            assert _run(os_approval_rollup.send_approval_rollups()) == 0
        send.assert_not_awaited()

    def test_pending_read_failure_returns_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ):
            assert _run(os_approval_rollup.send_approval_rollups()) == 0


class TestGatherSources:
    def test_all_source_kinds_collected(self):
        entries = [{"topic": "hours", "answer": "8-5 daily"}]
        with patch.object(
            os_research.os_custom_instructions, "kb_entries", return_value=entries
        ), patch.object(
            os_research.os_kb_feed, "tenant_kb_entries", return_value=entries
        ), patch.object(
            os_research.os_graph_memory,
            "graph_kb_entries",
            new=AsyncMock(return_value=entries),
        ), patch.object(
            os_research.os_mcp_context,
            "tool_context_entries",
            new=AsyncMock(return_value=entries),
        ):
            corpus, kinds = _run(os_research.gather_sources(_db({}), "c1", "hours"))
        assert kinds == [
            "department instructions",
            "knowledge base",
            "learned memory",
            "connected tools (MCP)",
        ]
        assert "8-5 daily" in corpus

    def test_each_source_failure_degrades_not_raises(self):
        boom = MagicMock(side_effect=RuntimeError("down"))
        with patch.object(
            os_research.os_custom_instructions, "kb_entries", boom
        ), patch.object(
            os_research.os_kb_feed, "tenant_kb_entries", boom
        ), patch.object(
            os_research.os_graph_memory,
            "graph_kb_entries",
            new=AsyncMock(side_effect=RuntimeError("down")),
        ), patch.object(
            os_research.os_mcp_context,
            "tool_context_entries",
            new=AsyncMock(side_effect=RuntimeError("down")),
        ):
            corpus, kinds = _run(os_research.gather_sources(_db({}), "c1", "hours"))
        assert corpus == "" and kinds == []

    def test_run_persist_failure_reports_error(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        fake = MagicMock()
        fake.text = "Brief."
        with patch.object(
            os_research,
            "gather_sources",
            new=AsyncMock(return_value=("[faq]\nhours", ["knowledge base"])),
        ), patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=fake),
        ):
            out = _run(
                os_research.run_research(db, "c1", "what do customers ask most?")
            )
        assert out["error"] == "could not save the research brief"


class TestChatDataAnswerEdges:
    def test_matched_but_error_result_passes_through(self):
        db = _db({})
        with patch.object(
            os_data_answers.biz_answers,
            "answer_question",
            return_value={"matched": True, "error": True, "answer": "x"},
        ):
            out = _run(
                os_data_answers.try_data_answer(
                    db, "c1", "th1", {"content": "how many leads this week?"}
                )
            )
        assert out is None

    def test_persist_failure_passes_through(self):
        calls = {"n": 0}

        def _table(name):
            calls["n"] += 1
            if name == "os_messages":
                raise RuntimeError("insert down")
            return _Query([{"id": "l1"}], [], name)

        db = MagicMock()
        db.table.side_effect = _table
        out = _run(
            os_data_answers.try_data_answer(
                db, "c1", "th1", {"content": "how many leads this week?"}
            )
        )
        assert out is None

    def test_empty_content_passes_through(self):
        assert (
            _run(os_data_answers.try_data_answer(_db({}), "c1", "th1", {"content": ""}))
            is None
        )


class TestRunnerFastPathWiring:
    def test_process_user_turn_returns_data_answer_before_engine(self):
        from backend.services import os_thread_runner

        reply = {
            "user_message": {"content": "how many leads?"},
            "assistant_message": {"id": "m2", "content": "4 leads."},
            "action": "answer",
            "agent_runs": [],
            "data_answer": True,
        }
        with patch(
            "backend.services.os_data_answers.try_data_answer",
            new=AsyncMock(return_value=reply),
        ), patch.object(
            os_thread_runner, "_mirror_to_channel", new=AsyncMock()
        ) as mirror:
            out = _run(
                os_thread_runner.process_user_turn(
                    _db({}), "c1", "th1", {"content": "how many leads?"}, None
                )
            )
        assert out is reply
        mirror.assert_awaited_once()


class TestProjectsRunnerEdges:
    def test_tick_survives_planning_crash(self):
        db = _db({"os_projects": []})
        with patch.object(
            os_projects,
            "plan_pending_projects",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            assert _run(os_projects.run_project_ticks(db)) == 0


class TestRollupEdges:
    def test_bad_timestamp_treated_as_young(self):
        assert os_approval_rollup._age_hours("not-a-date") == 0.0

    def test_run_without_client_id_skipped(self):
        db = TestApprovalRollup()._rollup_db([{"client_id": None, "created_at": "x"}])
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ):
            assert _run(os_approval_rollup.send_approval_rollups()) == 0

    def test_send_failure_not_counted(self):
        db = TestApprovalRollup()._rollup_db(
            [{"client_id": "c1", "created_at": TestApprovalRollup._OLD}]
        )
        with patch(
            "backend.services.os_approval_rollup.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.email_sender.send_email",
            new=AsyncMock(return_value={"success": False}),
        ):
            assert _run(os_approval_rollup.send_approval_rollups()) == 0


class TestPlanSchemaApiContract:
    def test_every_object_level_forbids_additional_properties(self):
        # Anthropic structured output 400s without this - caught by the
        # 2026-07-21 prod planner smoke, unreachable from mocked tests.
        schema = os_projects._PLAN_SCHEMA
        assert schema["additionalProperties"] is False
        assert schema["properties"]["steps"]["items"]["additionalProperties"] is False
