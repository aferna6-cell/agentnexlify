"""Suite-batch contracts: scheduled OS tasks, ask-data templates, MCP context
injection, customer memory, and FAQ auto-seeded evals."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import (
    biz_answers,
    customer_memory,
    kb_evals,
    os_mcp_context,
    os_scheduled_tasks,
)


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink=None):
        self._rows = rows
        self._sink = sink if sink is not None else []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows_by_table, sink=None):
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(
        rows_by_table.get(name, []), sink
    )
    return db


class TestScheduledTasks:
    def test_clamp_interval(self):
        assert os_scheduled_tasks.clamp_interval(0) == 1
        assert os_scheduled_tasks.clamp_interval(365) == 90
        assert os_scheduled_tasks.clamp_interval("junk") == 7

    def test_run_due_advances_cadence_before_running(self):
        sink: list = []
        task = {
            "id": "t1",
            "client_id": "c1",
            "department": "marketing",
            "prompt": "Draft this week's promo email",
            "interval_days": 7,
        }
        db = _db({"os_scheduled_tasks": [task]}, sink)
        with patch.object(
            os_scheduled_tasks, "run_task", new=AsyncMock(return_value=True)
        ) as runner:
            ran = asyncio.run(os_scheduled_tasks.run_due_tasks(db))
        assert ran == 1
        runner.assert_awaited_once()
        # next_run_at bumped via update BEFORE the engine call could fail-loop.
        assert any(name == "update" for name, _ in sink)

    def test_engine_failure_does_not_stop_batch(self):
        tasks = [
            {"id": "a", "client_id": "c1", "prompt": "p1", "interval_days": 7},
            {"id": "b", "client_id": "c1", "prompt": "p2", "interval_days": 7},
        ]
        db = _db({"os_scheduled_tasks": tasks})
        with patch.object(
            os_scheduled_tasks,
            "run_task",
            new=AsyncMock(side_effect=[RuntimeError("engine down"), True]),
        ):
            ran = asyncio.run(os_scheduled_tasks.run_due_tasks(db))
        assert ran == 1

    def test_run_task_drives_engine_turn_with_department(self):
        rows = {
            "os_threads": [{"id": "th1"}],
            "os_messages": [{"id": "m1", "content": "p"}],
        }
        db = _db(rows)
        turn = AsyncMock(return_value={})
        with patch(
            "backend.services.os_thread_runner.process_user_turn", new=turn
        ):
            ok = asyncio.run(
                os_scheduled_tasks.run_task(
                    db,
                    {
                        "client_id": "c1",
                        "prompt": "Chase stale quotes",
                        "department": "sales",
                    },
                )
            )
        assert ok is True
        assert turn.await_args.kwargs["force_agent_id"] == "sales"


class TestBizAnswers:
    def test_lead_count_template(self):
        db = _db({"leads": [{"id": 1}, {"id": 2}]})
        out = biz_answers.answer_question(db, "t1", "how many leads this week?")
        assert out["matched"] and out["template"] == "lead_count"
        assert out["data"] == {"leads": 2}
        assert "2 new lead(s)" in out["answer"]
        assert out["period"] == "week"

    def test_leads_by_source_orders_by_count(self):
        db = _db(
            {
                "leads": [
                    {"source": "google"},
                    {"source": "google"},
                    {"source": ""},
                ]
            }
        )
        out = biz_answers.answer_question(db, "t1", "where do my leads come from?")
        assert out["template"] == "leads_by_source"
        assert out["data"]["by_source"] == {"google": 2, "unknown": 1}

    def test_unmatched_returns_supported_not_a_guess(self):
        out = biz_answers.answer_question(_db({}), "t1", "what is the weather?")
        assert out["matched"] is False
        assert out["supported_questions"] == biz_answers.SUPPORTED

    def test_read_failure_reports_error_not_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        out = biz_answers.answer_question(db, "t1", "how many invoices this month")
        assert out.get("error") is True


class TestMcpContext:
    def test_entries_when_flag_on_and_servers_exist(self):
        db = _db({"tenant_mcp_servers": [{"name": "crm", "enabled": True}]})
        with patch.object(os_mcp_context, "flag_enabled", return_value=True):
            entries = os_mcp_context.kb_entries(db, "t1")
        assert len(entries) == 1
        assert "crm" in entries[0]["answer"]
        assert "Do not claim to have called" in entries[0]["answer"]

    def test_empty_when_flag_off(self):
        with patch.object(os_mcp_context, "flag_enabled", return_value=False):
            assert os_mcp_context.kb_entries(_db({}), "t1") == []

    def test_empty_when_no_servers(self):
        with patch.object(os_mcp_context, "flag_enabled", return_value=True):
            assert os_mcp_context.kb_entries(_db({}), "t1") == []


class TestCustomerMemory:
    def test_known_lead_profile_block(self):
        rows = {
            "conversations": [
                {
                    "session_id": "s1",
                    "lead_id": "l1",
                    "created_at": "2026-06-01T10:00:00Z",
                }
            ],
            "leads": [
                {
                    "name": "Sam Rivera",
                    "status": "qualified",
                    "areas_of_interest": ["cold brew"],
                }
            ],
        }
        block = customer_memory.profile_block(_db(rows), "t1", "s1")
        assert "Sam Rivera" in block
        assert "qualified" in block
        assert "cold brew" in block
        assert "2026-06-01" in block

    def test_unknown_session_returns_none(self):
        assert customer_memory.profile_block(_db({}), "t1", "s1") is None
        assert customer_memory.profile_block(_db({}), "t1", None) is None

    def test_read_failure_fails_open(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert customer_memory.profile_block(db, "t1", "s1") is None


class TestAutoSeedEvals:
    def test_seeds_from_faqs_when_empty(self):
        sink: list = []
        rows = {
            "tenant_eval_questions": [],
            "faq_entries": [
                {
                    "question": "What are your hours?",
                    "answer": "We are open Monday to Friday 8am to 5pm.",
                },
                {"question": "Hi", "answer": "short"},
            ],
        }
        created = kb_evals.auto_seed_from_faqs(_db(rows, sink), "t1")
        assert created == 1
        insert_calls = [args for name, args in sink if name == "insert"]
        seeded = insert_calls[0][0][0]
        assert seeded["question"] == "What are your hours?"
        assert seeded["expected_phrases"] == ["We are open Monday to Friday"]

    def test_never_pollutes_existing_suite(self):
        rows = {"tenant_eval_questions": [{"id": "q1"}]}
        assert kb_evals.auto_seed_from_faqs(_db(rows), "t1") == 0


class TestOsTasksRouter:
    _CLAIMS = {"tenant_id": "t1"}

    def test_create_list_delete_flow(self):
        from backend.routers import os_tasks
        from backend.routers.os_tasks import TaskIn

        created_row = {"id": "task1", "department": "sales", "prompt": "p" * 10}
        rows = {"os_scheduled_tasks": [created_row]}
        with patch.object(
            os_tasks, "get_service_supabase", return_value=_db(rows)
        ):
            listed = asyncio.run(os_tasks.list_tasks(claims=self._CLAIMS))
            assert listed["tasks"][0]["id"] == "task1"
            assert "sales" in listed["departments"]
            deleted = asyncio.run(
                os_tasks.delete_task("task1", claims=self._CLAIMS)
            )
            assert deleted == {"deleted": True}

    def test_create_validates_department_and_clamps_interval(self):
        import pytest
        from fastapi import HTTPException

        from backend.routers import os_tasks
        from backend.routers.os_tasks import TaskIn

        with pytest.raises(HTTPException) as err:
            asyncio.run(
                os_tasks.create_task(
                    TaskIn(department="hacking", prompt="do the thing"),
                    claims=self._CLAIMS,
                )
            )
        assert err.value.status_code == 422

        sink: list = []
        db = _db({"os_scheduled_tasks": [{"id": "new"}]}, sink)
        with patch.object(os_tasks, "get_service_supabase", return_value=db):
            asyncio.run(
                os_tasks.create_task(
                    TaskIn(
                        department="Sales", prompt="chase quotes", interval_days=400
                    ),
                    claims=self._CLAIMS,
                )
            )
        inserted = [args for name, args in sink if name == "insert"][0][0]
        assert inserted["department"] == "sales"
        assert inserted["interval_days"] == 90

    def test_delete_missing_404s(self):
        import pytest
        from fastapi import HTTPException

        from backend.routers import os_tasks

        with patch.object(
            os_tasks, "get_service_supabase", return_value=_db({})
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(os_tasks.delete_task("nope", claims=self._CLAIMS))
        assert err.value.status_code == 404


class TestAskDataRouter:
    def test_endpoints_proxy_service(self):
        from backend.routers import os_ask_data
        from backend.routers.os_ask_data import AskDataIn

        supported = asyncio.run(
            os_ask_data.supported_questions(claims={"tenant_id": "t1"})
        )
        assert supported["supported_questions"] == biz_answers.SUPPORTED

        with patch.object(
            os_ask_data, "get_service_supabase",
            return_value=_db({"leads": [{"id": 1}]}),
        ):
            out = asyncio.run(
                os_ask_data.ask_data(
                    AskDataIn(question="how many leads today?"),
                    claims={"tenant_id": "t1"},
                )
            )
        assert out["matched"] and out["period"] == "today"


class TestBizAnswersBranches:
    def test_all_templates_and_periods(self):
        db = _db(
            {
                "appointments": [{"id": 1}],
                "invoices": [{"id": 1}, {"id": 2}],
                "conversations": [{"id": 1}],
            }
        )
        appt = biz_answers.answer_question(db, "t1", "appointments this quarter?")
        assert appt["template"] == "appointment_count" and appt["period"] == "quarter"
        inv = biz_answers.answer_question(db, "t1", "how many invoices this month")
        assert inv["data"] == {"invoices": 2}
        convo = biz_answers.answer_question(db, "t1", "how many conversations this week")
        assert convo["data"] == {"conversations": 1}


class TestFailureBranches:
    def test_mcp_context_read_failure_fails_open(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        with patch.object(os_mcp_context, "flag_enabled", return_value=True):
            assert os_mcp_context.kb_entries(db, "t1") == []

    def test_customer_memory_lead_read_failure_still_returns_visit_block(self):
        convo = {
            "session_id": "s1",
            "lead_id": "l1",
            "created_at": "2026-06-01T10:00:00Z",
        }

        calls = {"n": 0}

        def _table(name):
            calls["n"] += 1
            if name == "leads" or calls["n"] > 1:
                raise RuntimeError("down")
            return _Query([convo])

        db = MagicMock()
        db.table.side_effect = _table
        block = customer_memory.profile_block(db, "t1", "s1")
        assert block and "2026-06-01" in block

    def test_auto_seed_read_and_insert_failures_return_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert kb_evals.auto_seed_from_faqs(db, "t1") == 0

        rows = {
            "tenant_eval_questions": [],
            "faq_entries": [
                {"question": "Hours?", "answer": "Open Monday to Friday 8-5 daily"}
            ],
        }

        def _table(name):
            if name == "tenant_eval_questions" and _table.reads > 0:
                raise RuntimeError("insert down")
            if name == "tenant_eval_questions":
                _table.reads += 1
            return _Query(rows.get(name, []))

        _table.reads = 0
        db2 = MagicMock()
        db2.table.side_effect = _table
        assert kb_evals.auto_seed_from_faqs(db2, "t1") == 0

    def test_scheduled_tasks_due_query_failure_returns_zero(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert asyncio.run(os_scheduled_tasks.run_due_tasks(db)) == 0

    def test_run_task_empty_prompt_skips(self):
        assert (
            asyncio.run(
                os_scheduled_tasks.run_task(_db({}), {"client_id": "c", "prompt": " "})
            )
            is False
        )
