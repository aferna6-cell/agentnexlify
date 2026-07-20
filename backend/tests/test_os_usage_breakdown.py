"""Per-department usage breakdown (enterprise-audit item 3) — aggregation
contracts + tenant scoping of the endpoint."""

import asyncio
from unittest.mock import MagicMock, patch

from backend.routers import os_usage_breakdown
from backend.routers.os_usage_breakdown import build_breakdown


class TestBuildBreakdown:
    def test_groups_runs_and_tokens_by_department(self):
        runs = [
            {"id": "r1", "agent_name": "sales"},
            {"id": "r2", "agent_name": "sales"},
            {"id": "r3", "agent_name": "marketing"},
        ]
        calls = [
            {"run_id": "r1", "input_tokens": 100, "output_tokens": 50},
            {"run_id": "r2", "input_tokens": 200, "output_tokens": 100},
            {"run_id": "r3", "input_tokens": 10, "output_tokens": 5},
        ]
        rows = build_breakdown(runs, calls)
        sales = next(r for r in rows if r["department"] == "sales")
        assert sales == {
            "department": "sales",
            "runs": 2,
            "input_tokens": 300,
            "output_tokens": 150,
        }
        # Highest spend sorts first.
        assert rows[0]["department"] == "sales"

    def test_orphan_calls_group_under_routing(self):
        rows = build_breakdown(
            [], [{"run_id": None, "input_tokens": 40, "output_tokens": 4}]
        )
        assert rows == [
            {
                "department": "routing",
                "runs": 0,
                "input_tokens": 40,
                "output_tokens": 4,
            }
        ]

    def test_run_with_no_calls_still_counted(self):
        rows = build_breakdown([{"id": "r1", "agent_name": "operations"}], [])
        assert rows[0]["runs"] == 1
        assert rows[0]["input_tokens"] == 0

    def test_empty_inputs(self):
        assert build_breakdown([], []) == []


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


class TestEndpoint:
    def test_breakdown_shape_and_cycle(self):
        rows_by_table = {
            "os_agent_runs": [{"id": "r1", "agent_name": "sales"}],
            "os_model_call_log": [
                {"run_id": "r1", "input_tokens": 7, "output_tokens": 3}
            ],
        }
        db = MagicMock()
        db.table.side_effect = lambda name: _Query(rows_by_table.get(name, []))
        with patch.object(
            os_usage_breakdown, "get_service_supabase", return_value=db
        ):
            out = asyncio.run(
                os_usage_breakdown.usage_breakdown(claims={"tenant_id": "t-1"})
            )
        assert out["departments"] == [
            {"department": "sales", "runs": 1, "input_tokens": 7, "output_tokens": 3}
        ]
        assert out["cycle_start"]

    def test_read_failure_degrades_to_empty(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("boom")
        with patch.object(
            os_usage_breakdown, "get_service_supabase", return_value=db
        ):
            out = asyncio.run(
                os_usage_breakdown.usage_breakdown(claims={"tenant_id": "t-1"})
            )
        assert out["departments"] == []
