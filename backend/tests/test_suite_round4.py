"""Round-4 contracts: chat-originated projects, research-to-project handoff,
marketing-gate alignment, and the runner wiring for the chat fast paths."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.services import os_chat_projects, os_research


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


# --- extract_project_ask (pure trigger parsing) -----------------------------


class TestExtractProjectAsk:
    def test_start_a_project_with_colon(self):
        out = os_chat_projects.extract_project_ask(
            "start a project: launch a spring promo"
        )
        assert out == "launch a spring promo"

    def test_plan_this_as_a_project_with_dash(self):
        out = os_chat_projects.extract_project_ask(
            "Plan this as a project - improve retention for regulars"
        )
        assert out == "improve retention for regulars"

    def test_create_a_project_strips_lead_in(self):
        out = os_chat_projects.extract_project_ask(
            "create a project to win back lapsed customers"
        )
        assert out == "win back lapsed customers"

    def test_kick_off_a_new_project(self):
        out = os_chat_projects.extract_project_ask(
            "kick off a new project: revamp the booking flow"
        )
        assert out == "revamp the booking flow"

    def test_case_insensitive(self):
        out = os_chat_projects.extract_project_ask(
            "START A PROJECT: Clean up the invoice backlog"
        )
        assert out == "Clean up the invoice backlog"

    def test_bare_trigger_returns_empty_string(self):
        assert os_chat_projects.extract_project_ask("start a project") == ""
        assert os_chat_projects.extract_project_ask("make this a project") == ""

    def test_ordinary_asks_do_not_trigger(self):
        for content in (
            "plan my week",
            "how do I start a project?",
            "we should start a project someday",
            "what projects are running?",
            "",
        ):
            assert os_chat_projects.extract_project_ask(content) is None


# --- try_start_project ------------------------------------------------------


_OWNER_THREAD = [{"id": "th1", "source": "chat"}]
_MSG = {"id": "m1", "content": "start a project: launch a spring promo"}


def _chat_db(
    thread_rows=_OWNER_THREAD,
    plan="agent_os",
    project_rows=None,
    sink=None,
):
    # os_projects rows serve BOTH the active-count read and the insert return,
    # so one queued row keeps the count under the cap while giving insert a
    # row to hand back.
    if project_rows is None:
        project_rows = [{"id": "p1", "status": "planning", "ask": "x"}]
    return _db(
        {
            "os_threads": thread_rows,
            "tenants": [{"plan": plan}] if plan else [],
            "os_projects": project_rows,
            "os_messages": [{"id": "m2", "content": "reply"}],
        },
        sink,
    )


def _start(db, content=None):
    msg = dict(_MSG)
    if content is not None:
        msg["content"] = content
    with patch(
        "backend.services.platform_flags.flag_enabled", return_value=True
    ):
        return _run(
            os_chat_projects.try_start_project(db, "c1", "th1", msg)
        )


class TestTryStartProject:
    def test_happy_path_queues_planning_project(self):
        sink: list = []
        db = _chat_db(sink=sink)
        out = _start(db)
        assert out is not None
        assert out["chat_project"] is True and out["action"] == "answer"
        assert out["project"]["id"] == "p1"
        assert "Project queued" in out["assistant_message"]["content"] or (
            "Project queued" in str(
                [s for s in sink if s[0] == "os_messages" and s[1] == "insert"]
            )
        )
        inserts = [s for s in sink if s[0] == "os_projects" and s[1] == "insert"]
        assert len(inserts) == 1
        assert inserts[0][2][0]["status"] == "planning"
        assert inserts[0][2][0]["ask"] == "launch a spring promo"

    def test_non_trigger_returns_none_without_db(self):
        db = MagicMock()
        out = _run(
            os_chat_projects.try_start_project(
                db, "c1", "th1", {"content": "plan my week"}
            )
        )
        assert out is None
        db.table.assert_not_called()

    def test_flag_off_falls_through_to_engine(self):
        db = _chat_db()
        with patch(
            "backend.services.platform_flags.flag_enabled", return_value=False
        ):
            out = _run(
                os_chat_projects.try_start_project(db, "c1", "th1", dict(_MSG))
            )
        assert out is None

    def test_inbound_customer_thread_never_starts_projects(self):
        for source in ("widget", "email", "sms", "facebook", "instagram"):
            db = _chat_db(thread_rows=[{"id": "th1", "source": source}])
            assert _start(db) is None

    def test_missing_thread_returns_none(self):
        db = _chat_db(thread_rows=[])
        assert _start(db) is None

    def test_chatbot_plan_gets_upgrade_reply_not_a_project(self):
        sink: list = []
        db = _chat_db(plan="chatbot", sink=sink)
        out = _start(db)
        assert out is not None
        assert "Agent OS plan" in out["assistant_message"]["content"] or (
            os_chat_projects.UPGRADE_REPLY
            in str([s for s in sink if s[1] == "insert"])
        )
        assert not [s for s in sink if s[0] == "os_projects" and s[1] == "insert"]

    def test_plan_read_failure_fails_open(self):
        sink: list = []
        db = _chat_db(sink=sink)
        original = db.table.side_effect

        def _table(name):
            if name == "tenants":
                raise RuntimeError("db down")
            return original(name)

        db.table.side_effect = _table
        out = _start(db)
        assert out is not None and out.get("project")

    def test_bare_trigger_gets_usage_guidance(self):
        sink: list = []
        db = _chat_db(sink=sink)
        out = _start(db, content="start a project")
        assert out is not None
        assert not [s for s in sink if s[0] == "os_projects" and s[1] == "insert"]

    def test_cap_reached_gets_cap_reply(self):
        sink: list = []
        rows = [{"id": f"p{i}"} for i in range(3)]
        db = _chat_db(project_rows=rows, sink=sink)
        out = _start(db)
        assert out is not None
        assert not [s for s in sink if s[0] == "os_projects" and s[1] == "insert"]

    def test_unexpected_failure_returns_none_engine_proceeds(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("boom")
        assert _start(db) is None

    def test_planning_counts_as_active_for_the_cap(self):
        from backend.services.os_projects import ACTIVE_STATUSES

        assert "planning" in ACTIVE_STATUSES


# --- runner wiring ----------------------------------------------------------


class TestRunnerWiring:
    def test_chat_project_short_circuits_engine(self):
        from backend.services import os_thread_runner

        turn = {"assistant_message": {"id": "m2"}, "chat_project": True}
        with patch(
            "backend.services.os_data_answers.try_data_answer",
            new=AsyncMock(return_value=None),
        ), patch(
            "backend.services.os_chat_projects.try_start_project",
            new=AsyncMock(return_value=turn),
        ) as start, patch(
            "backend.services.agent_sdk_client.is_configured"
        ) as configured:
            out = _run(
                os_thread_runner.process_user_turn(
                    MagicMock(), "c1", "th1", dict(_MSG), None
                )
            )
        assert out is turn
        start.assert_awaited_once()
        configured.assert_not_called()

    def test_forced_turns_skip_both_fast_paths(self):
        from backend.services import os_thread_runner

        with patch(
            "backend.services.os_data_answers.try_data_answer",
            new=AsyncMock(return_value=None),
        ) as data, patch(
            "backend.services.os_chat_projects.try_start_project",
            new=AsyncMock(return_value=None),
        ) as start, patch(
            "backend.services.os_thread_runner.connector_awareness"
        ), patch(
            "backend.services.agent_sdk_client.is_configured", return_value=False
        ), patch(
            "backend.services.os_thread_runner._degrade_offline",
            new=AsyncMock(return_value={"action": "answer"}),
        ):
            _run(
                os_thread_runner.process_user_turn(
                    MagicMock(),
                    "c1",
                    "th1",
                    dict(_MSG),
                    None,
                    force_agent_id="marketing",
                )
            )
        data.assert_not_awaited()
        start.assert_not_awaited()


# --- research_to_project ----------------------------------------------------


_BRIEF_RUN = {
    "id": "r1",
    "agent_name": "research",
    "deliverable": {
        "title": "Research brief: pricing strategy",
        "body": "Key findings: regulars respond to bundles.",
    },
}


class TestResearchToProject:
    def test_happy_path_seeds_project_from_brief(self):
        db = _db({"os_agent_runs": [_BRIEF_RUN]})
        planned = {"project": {"id": "p9", "status": "draft"}, "steps": []}
        with patch(
            "backend.services.os_projects.plan_project",
            new=AsyncMock(return_value=planned),
        ) as plan:
            out = _run(os_research.research_to_project(db, "c1", "r1"))
        assert out is planned
        ask = plan.await_args.args[2]
        assert "pricing strategy" in ask
        assert "regulars respond to bundles" in ask

    def test_ask_respects_max_len(self):
        run = {
            "id": "r1",
            "agent_name": "research",
            "deliverable": {"title": "Research brief: x", "body": "b" * 9000},
        }
        db = _db({"os_agent_runs": [run]})
        with patch(
            "backend.services.os_projects.plan_project",
            new=AsyncMock(return_value={}),
        ) as plan:
            _run(os_research.research_to_project(db, "c1", "r1"))
        from backend.services.os_projects import MAX_ASK_LEN

        assert len(plan.await_args.args[2]) <= MAX_ASK_LEN

    def test_missing_run_raises(self):
        db = _db({"os_agent_runs": []})
        with pytest.raises(ValueError):
            _run(os_research.research_to_project(db, "c1", "r1"))

    def test_non_research_run_raises(self):
        run = {**_BRIEF_RUN, "agent_name": "marketing"}
        db = _db({"os_agent_runs": [run]})
        with pytest.raises(ValueError):
            _run(os_research.research_to_project(db, "c1", "r1"))

    def test_empty_brief_raises(self):
        run = {
            "id": "r1",
            "agent_name": "research",
            "deliverable": {"title": "Research brief: x", "body": "  "},
        }
        db = _db({"os_agent_runs": [run]})
        with pytest.raises(ValueError):
            _run(os_research.research_to_project(db, "c1", "r1"))


# --- research router: to-project endpoint -----------------------------------


class TestResearchToProjectRouter:
    def _client(self):
        from backend.dependencies import _get_current_tenant
        from backend.main import app
        from backend.services.agent_os_gate import require_agent_os_access
        from backend.tests.conftest import SyncASGITestClient

        claims = {"tenant_id": "11111111-1111-1111-1111-111111111111"}
        app.dependency_overrides[_get_current_tenant] = lambda: claims
        app.dependency_overrides[require_agent_os_access] = lambda: claims
        return SyncASGITestClient(app)

    def teardown_method(self):
        from backend.dependencies import _get_current_tenant
        from backend.main import app
        from backend.services.agent_os_gate import require_agent_os_access

        app.dependency_overrides.pop(_get_current_tenant, None)
        app.dependency_overrides.pop(require_agent_os_access, None)

    def test_flag_off_404(self):
        client = self._client()
        with patch(
            "backend.routers.os_research.flag_enabled", return_value=False
        ):
            resp = client.post("/api/v1/os/research/r1/to-project")
        assert resp.status_code == 404

    def test_happy_path_returns_planned_project(self):
        client = self._client()
        planned = {"project": {"id": "p9", "status": "draft"}, "steps": []}
        with patch(
            "backend.routers.os_research.flag_enabled", return_value=True
        ), patch(
            "backend.routers.os_research.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_research.research_to_project",
            new=AsyncMock(return_value=planned),
        ):
            resp = client.post("/api/v1/os/research/r1/to-project")
        assert resp.status_code == 200
        assert resp.json()["project"]["id"] == "p9"

    def test_value_error_maps_to_422(self):
        client = self._client()
        with patch(
            "backend.routers.os_research.flag_enabled", return_value=True
        ), patch(
            "backend.routers.os_research.get_service_supabase",
            return_value=MagicMock(),
        ), patch(
            "backend.routers.os_research.research_to_project",
            new=AsyncMock(side_effect=ValueError("research brief not found")),
        ):
            resp = client.post("/api/v1/os/research/missing/to-project")
        assert resp.status_code == 422
