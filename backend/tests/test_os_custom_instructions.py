"""Topics-lite custom instructions (enterprise-audit item 4) + trace endpoint
(item 1) — contracts."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from backend.routers import os_run_trace
from backend.services import os_custom_instructions as oci


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


def _tenants_db(instructions, sink=None):
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(
        [{"os_custom_instructions": instructions}], sink
    )
    return db


class TestGetInstructions:
    def test_returns_known_departments_only(self):
        db = _tenants_db(
            {"sales": "Mention referrals.", "bogus_dept": "x", "marketing": "  "}
        )
        assert oci.get_instructions(db, "t1") == {"sales": "Mention referrals."}

    def test_caps_length(self):
        db = _tenants_db({"sales": "x" * 5000})
        out = oci.get_instructions(db, "t1")
        assert len(out["sales"]) == oci.MAX_INSTRUCTION_LEN

    def test_read_failure_returns_empty(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("down")
        assert oci.get_instructions(db, "t1") == {}


class TestSetInstruction:
    def test_unknown_department_rejected(self):
        with pytest.raises(oci.UnknownDepartment):
            oci.set_instruction(_tenants_db({}), "t1", "hacking", "x")

    def test_set_then_clear(self):
        sink: list = []
        db = _tenants_db({}, sink)
        out = oci.set_instruction(db, "t1", "Sales", "Always offer the referral link")
        assert out == {"sales": "Always offer the referral link"}
        assert any(name == "update" for name, _ in sink)

        db2 = _tenants_db({"sales": "old"}, sink)
        out2 = oci.set_instruction(db2, "t1", "sales", "   ")
        assert out2 == {}


class TestKbEntries:
    def test_entries_carry_invariant_wrapper_and_sort(self):
        db = _tenants_db({"sales": "Push gift cards.", "marketing": "Be warm."})
        entries = oci.kb_entries(db, "t1")
        assert [e["topic"] for e in entries] == [
            "owner instructions: marketing",
            "owner instructions: sales",
        ]
        assert "never override approval requirements" in entries[0]["answer"]
        assert "Be warm." in entries[0]["answer"]

    def test_empty_map_yields_no_entries(self):
        assert oci.kb_entries(_tenants_db({}), "t1") == []


class TestRunTraceEndpoint:
    def _db(self, rows_by_table):
        db = MagicMock()
        db.table.side_effect = lambda name: _Query(rows_by_table.get(name, []))
        return db

    def test_trace_assembles_all_layers(self):
        rows = {
            "os_agent_runs": [{"id": "r1", "agent_name": "sales"}],
            "os_routing_decision": [{"chosen_agent": "sales"}],
            "os_model_call_log": [{"purpose": "draft", "input_tokens": 5}],
            "os_action_runs": [{"action_type": "email.send", "status": "succeeded"}],
            "os_messages": [{"role": "assistant", "content": "Done."}],
        }
        with patch.object(
            os_run_trace, "get_service_supabase", return_value=self._db(rows)
        ):
            out = asyncio.run(
                os_run_trace.get_run_trace("r1", claims={"tenant_id": "t1"})
            )
        assert out["run"]["agent_name"] == "sales"
        assert out["routing_decisions"] and out["model_calls"]
        assert out["action_runs"][0]["status"] == "succeeded"
        assert out["messages"][0]["content"] == "Done."

    def test_missing_run_404s(self):
        from fastapi import HTTPException

        with patch.object(
            os_run_trace, "get_service_supabase", return_value=self._db({})
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(
                    os_run_trace.get_run_trace("nope", claims={"tenant_id": "t1"})
                )
        assert err.value.status_code == 404
