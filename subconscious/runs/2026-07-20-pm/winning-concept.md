# Winning Concept — 2026-07-20-pm

## Recommendation
Wire `mcp_client.py` into `os_thread_runner.py` and `agent_os_bridge.py` so that Agent OS tenants can actually execute MCP tool calls during conversations.

## Why This, Why Now
PR #514 (b17ed5c, shipped 2026-07-20) delivered MCP client infrastructure as one of 7 flagship enterprise features, but grep confirms zero imports of `mcp_client` in either execution-path file (`os_thread_runner.py` or `agent_os_bridge.py`). The configuration layer is complete — tenants can register MCP servers via the admin UI — but the execution layer is missing, making the feature entirely inert on day zero. This is a confirmed Day-0 bug, not a speculative risk: any tenant who configures an MCP tool today will see silent non-execution. The enterprise audit (PR #513) ranked MCP tool execution as competitive gap #4 vs Amazon/Microsoft/Google/Salesforce; closing it now, the same day the config shipped, prevents the gap from widening into a customer trust issue.

## Implementation Sketch
1. Read `backend/services/os_thread_runner.py` — find the tool-dispatch loop where tool calls are routed
2. Read `backend/services/agent_os_bridge.py` — confirm the `apply_outbound_guard` integration point at line 393
3. Read `backend/services/mcp_client.py` — understand the `execute_tool(tool_name, tool_input, server_config)` interface
4. In `os_thread_runner.py`: add `from backend.services.mcp_client import MCPClient` and a new dispatch branch: `if tool_call.get("type") == "mcp": result = await mcp_client.execute_tool(...)` — keep additive, don't touch existing dispatch
5. In `agent_os_bridge.py`: ensure the MCP dispatch result goes through `apply_outbound_guard` (line 393) before being returned to the conversation
6. Add trace logging for MCP tool calls (consistent with existing `os_model_call_log` pattern)
7. Write test in `backend/tests/test_agent_os.py` that mocks MCP server response and verifies the tool result appears in the conversation output
8. Verify `backend/tests/` passes; verify no imports of `from __future__ import annotations` introduced

## What This Replaces
Previous active direction: "Step 9F — KB autopopulate staleness check in nightly-commit-review SKILL.md" — that direction was fully implemented in run 99 (confirmed by grep: 6 occurrences in SKILL.md). This direction closes a new Day-0 execution gap from the same sprint that triggered the last direction.

## Confidence
HIGH — confirmed by grep (zero MCP client imports in execution path), bounded implementation (additive dispatch branch, ~30 lines), existing infrastructure handles error/timeout/guard.
