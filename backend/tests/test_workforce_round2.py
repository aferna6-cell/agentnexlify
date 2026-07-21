"""Round-2 contracts: workforce digest section, ask-data v2 templates,
starter recurring-task suggestions."""

from unittest.mock import MagicMock, patch

from backend.services import biz_answers, os_starter_tasks, workforce_digest


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


class TestWorkforceDigest:
    def test_idle_tenant_returns_none(self):
        db = _db({})
        assert workforce_digest.build_workforce_html(db, "t1") is None

    def test_active_tenant_gets_all_sections(self):
        db = _db(
            {
                "os_agent_runs": [
                    {"agent_name": "marketing", "created_at": "2026-07-20T00:00:00+00:00"},
                    {"agent_name": "sales", "created_at": "2026-07-18T00:00:00+00:00"},
                ],
                "os_outbound_log": [{"id": "o1"}],
                "os_scheduled_tasks": [{"last_run_at": "2026-07-20T00:00:00+00:00"}],
                "os_projects": [{"id": "p1"}],
            }
        )
        html = workforce_digest.build_workforce_html(db, "t1")
        assert "<b>2</b>" in html and "marketing" in html
        assert "recurring task" in html
        assert "went out" in html
        assert "project" in html
        # Same rows also matched the pending-approval read in this mock, so
        # the approval nudge renders with a review link.
        assert "waiting for" in html and "Review them" in html

    def test_pending_only_still_renders_nudge(self):
        # Runs exist but count 0 by dept? Use pending rows via os_agent_runs
        db = _db(
            {
                "os_agent_runs": [
                    {"agent_name": "sales", "created_at": "2026-07-01T00:00:00+00:00"}
                ]
            }
        )
        html = workforce_digest.build_workforce_html(db, "t1")
        assert "waiting for" in html
        # Oldest pending is weeks old - staleness callout included.
        assert "waited" in html

    def test_total_read_failure_returns_none(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        assert workforce_digest.build_workforce_html(db, "t1") is None


class TestAskDataV2Matching:
    def test_revenue_beats_invoice_template(self):
        assert biz_answers.match_template("how much revenue this month?") == "revenue"
        assert biz_answers.match_template("how much money did we make?") == "revenue"

    def test_comparison_matched(self):
        assert (
            biz_answers.match_template("how do leads compare to last week?")
            == "lead_comparison"
        )

    def test_upcoming_matched_before_appointment_count(self):
        assert (
            biz_answers.match_template("what appointments are coming up?")
            == "upcoming_appointments"
        )

    def test_plain_invoice_count_still_matches(self):
        assert biz_answers.match_template("how many invoices this month") == "invoice_count"


class TestAskDataV2Answers:
    def test_revenue_sums_paid_and_outstanding(self):
        db = _db(
            {
                "invoices": [
                    {"total": "100.50", "status": "paid"},
                    {"total": 49.50, "status": "paid"},
                    {"total": 200, "status": "sent"},
                    {"total": 75, "status": "draft"},
                ]
            }
        )
        out = biz_answers.answer_question(db, "c1", "how much revenue this month?")
        assert out["matched"] is True
        assert out["data"] == {"collected": 150.0, "outstanding": 200.0}
        assert "$150.00" in out["answer"] and "$200.00" in out["answer"]

    def test_revenue_no_outstanding_omits_clause(self):
        db = _db({"invoices": [{"total": 80, "status": "paid"}]})
        out = biz_answers.answer_question(db, "c1", "total sales this week")
        assert "outstanding" not in out["answer"]

    def test_comparison_reports_direction(self):
        calls = {"n": 0}

        def _table(name):
            calls["n"] += 1
            # First leads read = current period (3 rows), second = previous (1).
            rows = [{"id": i} for i in range(3 if calls["n"] == 1 else 1)]
            return _Query(rows, [], name)

        db = MagicMock()
        db.table.side_effect = _table
        out = biz_answers.answer_question(db, "c1", "compare my leads to last week")
        assert out["data"] == {"current": 3, "previous": 1, "delta": 2}
        assert "up" in out["answer"]

    def test_comparison_flat(self):
        db = _db({"leads": []})
        out = biz_answers.answer_question(db, "c1", "leads vs last month")
        assert out["data"]["delta"] == 0
        assert "flat" in out["answer"]

    def test_upcoming_appointments_counted(self):
        db = _db({"appointments": [{"id": "a1"}, {"id": "a2"}]})
        out = biz_answers.answer_question(db, "c1", "what's coming up this week?")
        assert out["data"] == {"upcoming": 2}
        assert "next 7 days" in out["answer"]

    def test_new_templates_listed_in_supported(self):
        joined = " ".join(biz_answers.SUPPORTED)
        assert "revenue" in joined and "compare" in joined and "coming up" in joined


class TestStarterRecurringTasks:
    def test_existing_task_suppresses_suggestions(self):
        db = _db({"os_scheduled_tasks": [{"id": "t1"}]})
        assert os_starter_tasks.suggest_recurring_tasks(db, "c1") == []

    def test_no_leads_gets_marketing_and_operations(self):
        db = _db(
            {
                "os_scheduled_tasks": [],
                "tenants": [{"business_type": "coffee_shop"}],
                "leads": [],
            }
        )
        out = os_starter_tasks.suggest_recurring_tasks(db, "c1")
        assert [s["department"] for s in out] == ["marketing", "operations"]
        assert "coffee shop" in out[0]["prompt"]
        assert all(s["interval_days"] == 7 for s in out)

    def test_leads_on_file_gets_sales_sweep(self):
        counts = {"leads": 5}

        def _table(name):
            if name == "os_scheduled_tasks":
                return _Query([], [], name)
            if name == "tenants":
                return _Query([{"business_type": "plumber"}], [], name)
            q = _Query([], [], name)
            # emulate count="exact" result for leads
            result = MagicMock()
            result.count = counts.get(name, 0)
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.limit.return_value = chain
            chain.execute.return_value = result
            return chain if name == "leads" else q

        db = MagicMock()
        db.table.side_effect = _table
        out = os_starter_tasks.suggest_recurring_tasks(db, "c1")
        assert [s["department"] for s in out] == ["marketing", "sales"]

    def test_db_failure_returns_empty(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert os_starter_tasks.suggest_recurring_tasks(db, "c1") == []
