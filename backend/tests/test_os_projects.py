"""OS Projects contracts (specs/os-projects_spec.md): plan validation,
sequential runner, approval-driven advancement, cancel semantics."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import os_projects


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Chainable query mock that records calls and returns canned rows."""

    def __init__(self, table, rows, sink):
        self._table = table
        self._rows = rows
        self._sink = sink

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
    db.table.side_effect = lambda name: _Query(name, rows_by_table.get(name, []), sink)
    db._sink = sink
    return db


PLAN_JSON = json.dumps(
    {
        "title": "Spring promo launch",
        "steps": [
            {"department": "marketing", "objective": "Draft the promo email"},
            {"department": "sales", "objective": "Draft follow-ups for warm leads"},
        ],
    }
)


class TestParsePlan:
    def test_valid_plan_parses(self):
        plan = os_projects.parse_plan(PLAN_JSON)
        assert plan["title"] == "Spring promo launch"
        assert [s["department"] for s in plan["steps"]] == ["marketing", "sales"]

    def test_code_fence_stripped(self):
        plan = os_projects.parse_plan(f"```json\n{PLAN_JSON}\n```")
        assert len(plan["steps"]) == 2

    def test_unknown_department_rejects_whole_plan(self):
        bad = json.dumps(
            {
                "title": "x",
                "steps": [
                    {"department": "marketing", "objective": "Draft the email"},
                    {"department": "wizardry", "objective": "Cast a spell"},
                ],
            }
        )
        with pytest.raises(ValueError, match="unknown department"):
            os_projects.parse_plan(bad)

    def test_too_few_steps_rejected(self):
        bad = json.dumps(
            {"title": "x", "steps": [{"department": "sales", "objective": "One thing"}]}
        )
        with pytest.raises(ValueError, match="steps"):
            os_projects.parse_plan(bad)

    def test_too_many_steps_rejected(self):
        bad = json.dumps(
            {
                "title": "x",
                "steps": [
                    {"department": "sales", "objective": f"Objective {i}"}
                    for i in range(7)
                ],
            }
        )
        with pytest.raises(ValueError, match="steps"):
            os_projects.parse_plan(bad)

    def test_non_json_rejected(self):
        with pytest.raises(ValueError, match="not JSON"):
            os_projects.parse_plan("here is your plan: do marketing then sales")

    def test_short_objective_rejected(self):
        bad = json.dumps(
            {
                "title": "x",
                "steps": [
                    {"department": "sales", "objective": "ok"},
                    {"department": "marketing", "objective": "Draft it properly"},
                ],
            }
        )
        with pytest.raises(ValueError, match="objective"):
            os_projects.parse_plan(bad)


class TestPlanProject:
    def test_short_ask_rejected(self):
        with pytest.raises(ValueError, match="ask too short"):
            _run(os_projects.plan_project(_db({}), "c1", "hey"))

    def test_active_cap_enforced(self):
        db = _db({"os_projects": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]})
        with pytest.raises(ValueError, match="active project limit"):
            _run(os_projects.plan_project(db, "c1", "launch a spring promo please"))

    def test_planner_success_persists_steps(self):
        sink: list = []
        project_row = {"id": "p1", "client_id": "c1", "status": "draft"}

        call_count = {"n": 0}

        def _table(name):
            if name == "os_projects":
                call_count["n"] += 1
                # First call: active-cap check (empty). Later: insert/update.
                rows = [] if call_count["n"] == 1 else [project_row]
                return _Query(name, rows, sink)
            return _Query(name, [], sink)

        db = MagicMock()
        db.table.side_effect = _table

        fake_result = MagicMock()
        fake_result.text = PLAN_JSON
        with patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=fake_result),
        ):
            out = _run(
                os_projects.plan_project(db, "c1", "launch a spring promo campaign")
            )
        assert out["project"]["title"] == "Spring promo launch"
        assert len(out["steps"]) == 2
        assert out["steps"][0]["position"] == 1
        assert out["steps"][0]["client_id"] == "c1"

    def test_planner_failure_leaves_draft_with_error_and_no_steps(self):
        sink: list = []
        project_row = {"id": "p1", "client_id": "c1", "status": "draft"}
        call_count = {"n": 0}

        def _table(name):
            if name == "os_projects":
                call_count["n"] += 1
                rows = [] if call_count["n"] == 1 else [project_row]
                return _Query(name, rows, sink)
            return _Query(name, [], sink)

        db = MagicMock()
        db.table.side_effect = _table

        with patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(side_effect=RuntimeError("model down")),
        ):
            out = _run(os_projects.plan_project(db, "c1", "launch a spring promo"))
        assert out["steps"] == []
        assert "planner failed" in out["project"]["error"]
        step_inserts = [s for s in sink if s[0] == "os_project_steps" and s[1] == "insert"]
        assert step_inserts == []


def _project(status="approved"):
    return {"id": "p1", "client_id": "c1", "ask": "launch promo", "title": "Promo",
            "status": status}


class TestAdvanceProject:
    def test_runs_first_pending_step_and_parks_on_approval(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "marketing", "objective": "Draft email", "status": "pending"},
            {"id": "s2", "client_id": "c1", "project_id": "p1", "position": 2,
             "department": "sales", "objective": "Follow ups", "status": "pending"},
        ]
        sink: list = []
        db = _db(
            {
                "os_project_steps": steps,
                "os_threads": [{"id": "t1"}],
                "os_messages": [{"id": "m1", "content": "x"}],
            },
            sink,
        )
        turn = AsyncMock(
            return_value={
                "agent_runs": [{"id": "r1", "deliverable_status": "pending_approval"}]
            }
        )
        with patch(
            "backend.services.os_thread_runner.process_user_turn", new=turn
        ):
            _run(os_projects.advance_project(db, _project()))
        assert turn.await_count == 1
        assert turn.await_args.kwargs.get("force_agent_id") == "marketing"
        # Step 1 parked awaiting approval; step 2 untouched this tick.
        assert steps[0]["status"] == "awaiting_approval"
        assert steps[0]["agent_run_id"] == "r1"
        assert steps[1]["status"] == "pending"

    def test_step_with_no_deliverable_completes_immediately(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "operations", "objective": "Summarize week",
             "status": "pending"},
        ]
        db = _db(
            {
                "os_project_steps": steps,
                "os_threads": [{"id": "t1"}],
                "os_messages": [{"id": "m1", "content": "x"}],
            }
        )
        turn = AsyncMock(return_value={"agent_runs": []})
        with patch("backend.services.os_thread_runner.process_user_turn", new=turn):
            _run(os_projects.advance_project(db, _project()))
        assert steps[0]["status"] == "done"

    def test_awaiting_step_blocks_until_deliverable_approved(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "marketing", "objective": "Draft email",
             "status": "awaiting_approval", "agent_run_id": "r1"},
        ]
        db = _db(
            {
                "os_project_steps": steps,
                "os_agent_runs": [{"deliverable_status": "pending_approval"}],
            }
        )
        turn = AsyncMock()
        with patch("backend.services.os_thread_runner.process_user_turn", new=turn):
            _run(os_projects.advance_project(db, _project("running")))
        turn.assert_not_awaited()
        assert steps[0]["status"] == "awaiting_approval"

    def test_approved_deliverable_completes_project(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "marketing", "objective": "Draft email",
             "status": "awaiting_approval", "agent_run_id": "r1"},
        ]
        sink: list = []
        db = _db(
            {
                "os_project_steps": steps,
                "os_agent_runs": [{"deliverable_status": "approved"}],
            },
            sink,
        )
        _run(os_projects.advance_project(db, _project("running")))
        assert steps[0]["status"] == "done"
        project_updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("done" in str(u[2]) for u in project_updates)

    def test_rejected_deliverable_fails_step_and_project(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "marketing", "objective": "Draft email",
             "status": "awaiting_approval", "agent_run_id": "r1"},
            {"id": "s2", "client_id": "c1", "project_id": "p1", "position": 2,
             "department": "sales", "objective": "Follow ups", "status": "pending"},
        ]
        sink: list = []
        db = _db(
            {
                "os_project_steps": steps,
                "os_agent_runs": [{"deliverable_status": "rejected"}],
            },
            sink,
        )
        turn = AsyncMock()
        with patch("backend.services.os_thread_runner.process_user_turn", new=turn):
            _run(os_projects.advance_project(db, _project("running")))
        turn.assert_not_awaited()
        assert steps[0]["status"] == "failed"
        project_updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("failed" in str(u[2]) for u in project_updates)

    def test_engine_failure_fails_step_and_project(self):
        steps = [
            {"id": "s1", "client_id": "c1", "project_id": "p1", "position": 1,
             "department": "marketing", "objective": "Draft email",
             "status": "pending"},
        ]
        sink: list = []
        db = _db(
            {
                "os_project_steps": steps,
                "os_threads": [{"id": "t1"}],
                "os_messages": [{"id": "m1", "content": "x"}],
            },
            sink,
        )
        turn = AsyncMock(side_effect=RuntimeError("engine offline"))
        with patch("backend.services.os_thread_runner.process_user_turn", new=turn):
            _run(os_projects.advance_project(db, _project()))
        step_updates = [
            s for s in sink if s[0] == "os_project_steps" and s[1] == "update"
        ]
        assert any("failed" in str(u[2]) for u in step_updates)
        project_updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("failed" in str(u[2]) for u in project_updates)

    def test_no_steps_fails_project(self):
        sink: list = []
        db = _db({"os_project_steps": []}, sink)
        _run(os_projects.advance_project(db, _project()))
        project_updates = [s for s in sink if s[0] == "os_projects" and s[1] == "update"]
        assert any("no steps" in str(u[2]) for u in project_updates)


class TestRunProjectTicks:
    def test_advances_each_active_project(self):
        projects = [_project(), {**_project(), "id": "p2"}]
        db = _db({"os_projects": projects})
        with patch.object(
            os_projects, "advance_project", new=AsyncMock()
        ) as advance:
            count = _run(os_projects.run_project_ticks(db))
        assert count == 2
        assert advance.await_count == 2

    def test_one_bad_project_does_not_stop_others(self):
        projects = [_project(), {**_project(), "id": "p2"}]
        db = _db({"os_projects": projects})
        with patch.object(
            os_projects,
            "advance_project",
            new=AsyncMock(side_effect=[RuntimeError("boom"), None]),
        ):
            count = _run(os_projects.run_project_ticks(db))
        assert count == 1

    def test_db_read_failure_returns_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert _run(os_projects.run_project_ticks(db)) == 0


class TestStepPrompt:
    def test_prompt_carries_ask_objective_and_summaries(self):
        prompt = os_projects._step_prompt(
            _project(),
            {"position": 2, "department": "sales", "objective": "Draft follow-ups"},
            ["Step 1 (marketing) produced: Promo email - Hello spring..."],
        )
        assert "launch promo" in prompt
        assert "Draft follow-ups" in prompt
        assert "Promo email" in prompt

    def test_summaries_truncate_body(self):
        steps = [
            {"id": "s1", "position": 1, "department": "marketing",
             "status": "done", "agent_run_id": "r1"},
        ]
        db = _db(
            {
                "os_agent_runs": [
                    {"deliverable": {"title": "Email", "body": "x" * 1000}}
                ]
            }
        )
        summaries = os_projects._completed_summaries(db, "c1", steps)
        assert len(summaries) == 1
        assert len(summaries[0]) < 400
