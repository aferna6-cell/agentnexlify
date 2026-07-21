"""Customer-memory write-back (propose-only) + MCP context-tool contracts."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import customer_memory, os_mcp_context, os_opportunities


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
    def __init__(self, rows, sink=None, table=None):
        self._rows = rows
        self._sink = sink if sink is not None else []
        self._table = table

    @property
    def not_(self):
        return self

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


_SERVICES = [{"name": "Gutter Cleaning"}, {"name": "Roof Repair"}]
_CONVO = [{"session_id": "sess1", "lead_id": "l1"}]


class TestDetectInterestWritebacks:
    def test_detects_mentioned_service_missing_from_lead(self):
        db = _db(
            {
                "service_types": _SERVICES,
                "conversations": _CONVO,
                "leads": [{"id": "l1", "name": "Sam", "areas_of_interest": []}],
                "chat_messages": [
                    {"role": "user", "content": "do you also do gutter cleaning?"},
                    {"role": "assistant", "content": "Yes we do!"},
                ],
            }
        )
        findings = customer_memory.detect_interest_writebacks(db, "t1")
        assert findings == [
            {"lead_id": "l1", "lead_name": "Sam", "new_interests": ["Gutter Cleaning"]}
        ]

    def test_existing_interest_not_reproposed(self):
        db = _db(
            {
                "service_types": _SERVICES,
                "conversations": _CONVO,
                "leads": [
                    {
                        "id": "l1",
                        "name": "Sam",
                        "areas_of_interest": ["gutter cleaning"],
                    }
                ],
                "chat_messages": [
                    {"role": "user", "content": "about that gutter cleaning quote"},
                ],
            }
        )
        assert customer_memory.detect_interest_writebacks(db, "t1") == []

    def test_assistant_mentions_do_not_count(self):
        db = _db(
            {
                "service_types": _SERVICES,
                "conversations": _CONVO,
                "leads": [{"id": "l1", "name": "Sam", "areas_of_interest": []}],
                "chat_messages": [
                    {"role": "assistant", "content": "We offer roof repair too."},
                    {"role": "user", "content": "just here about my invoice"},
                ],
            }
        )
        assert customer_memory.detect_interest_writebacks(db, "t1") == []

    def test_no_service_types_returns_empty(self):
        db = _db({"service_types": [], "conversations": _CONVO})
        assert customer_memory.detect_interest_writebacks(db, "t1") == []


class TestWritebackSuggestion:
    def test_none_when_no_findings(self):
        assert customer_memory.writeback_suggestion([]) is None

    def test_suggestion_names_leads_and_interests(self):
        s = customer_memory.writeback_suggestion(
            [{"lead_id": "l1", "lead_name": "Sam", "new_interests": ["Roof Repair"]}]
        )
        assert customer_memory.WRITEBACK_SUMMARY_PREFIX in s["summary"]
        assert "Sam: Roof Repair" in s["detail"]

    def test_kind_classification_matches_scanner(self):
        s = customer_memory.writeback_suggestion(
            [{"lead_id": "l1", "lead_name": "Sam", "new_interests": ["Roof Repair"]}]
        )
        assert os_opportunities._suggestion_kind(s["summary"]) == "memory_writeback"


class TestApplyInterestWritebacks:
    def test_appends_only_new_interests(self):
        sink: list = []
        db = _db(
            {
                "service_types": _SERVICES,
                "conversations": _CONVO,
                "leads": [
                    {
                        "id": "l1",
                        "name": "Sam",
                        "areas_of_interest": ["Landscaping"],
                    }
                ],
                "chat_messages": [
                    {"role": "user", "content": "interested in roof repair"},
                ],
            },
            sink,
        )
        updated = customer_memory.apply_interest_writebacks(db, "t1")
        assert updated == 1
        lead_updates = [s for s in sink if s[0] == "leads" and s[1] == "update"]
        assert lead_updates
        merged = lead_updates[0][2][0]["areas_of_interest"]
        assert merged == ["Landscaping", "Roof Repair"]

    def test_no_findings_updates_nothing(self):
        db = _db({"service_types": [], "conversations": []})
        assert customer_memory.apply_interest_writebacks(db, "t1") == 0


class TestComputeSuggestionsRule3:
    def test_writeback_suggestion_included(self):
        db = _db({"leads": [], "invoices": []})
        findings = [
            {"lead_id": "l1", "lead_name": "Sam", "new_interests": ["Roof Repair"]}
        ]
        with patch.object(
            customer_memory, "detect_interest_writebacks", return_value=findings
        ):
            suggestions = os_opportunities.compute_suggestions(db, "c1")
        assert any(
            customer_memory.WRITEBACK_SUMMARY_PREFIX in s["summary"]
            for s in suggestions
        )


class TestMcpContextTool:
    def _rows(self):
        return [
            {
                "name": "crm",
                "url": "https://mcp.example.com/mcp",
                "auth_header": "Authorization",
                "auth_token": None,
                "context_tool": "list_recent_orders",
                "context_args": {"limit": 5},
            }
        ]

    def test_flag_off_returns_empty(self):
        db = _db({"tenant_mcp_servers": self._rows()})
        with patch.object(os_mcp_context, "flag_enabled", return_value=False):
            assert _run(os_mcp_context.tool_context_entries(db, "t1")) == []

    def test_tool_result_injected_as_entry(self):
        db = _db({"tenant_mcp_servers": self._rows()})
        result = {"content": [{"type": "text", "text": "3 orders this week"}]}
        with patch.object(os_mcp_context, "flag_enabled", return_value=True), patch(
            "backend.services.mcp_client.call_tool",
            new=AsyncMock(return_value=result),
        ) as call:
            entries = _run(os_mcp_context.tool_context_entries(db, "t1"))
        assert call.await_args.args[1] == "list_recent_orders"
        assert call.await_args.args[2] == {"limit": 5}
        assert len(entries) == 1
        assert "3 orders this week" in entries[0]["answer"]

    def test_tool_failure_degrades_to_empty(self):
        db = _db({"tenant_mcp_servers": self._rows()})
        with patch.object(os_mcp_context, "flag_enabled", return_value=True), patch(
            "backend.services.mcp_client.call_tool",
            new=AsyncMock(side_effect=RuntimeError("server down")),
        ):
            assert _run(os_mcp_context.tool_context_entries(db, "t1")) == []

    def test_render_result_truncates(self):
        long = {"content": [{"type": "text", "text": "x" * 5000}]}
        assert len(os_mcp_context._render_result(long)) <= 1500

    def test_render_result_plain_dict(self):
        assert "42" in os_mcp_context._render_result({"count": 42})
