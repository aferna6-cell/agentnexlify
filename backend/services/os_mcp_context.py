"""MCP tool awareness + owner-designated context tools for Agent OS runs.

Phase 1 (awareness): injects the tenant's enabled MCP servers into
SharedContext.kb so every department KNOWS what external tools exist and
proposes their use in deliverables. Deterministic single-table read; no
network on the turn path.

Phase 2 (context tools, migration 184): the owner may designate ONE
read-only tool per server (``context_tool`` + fixed ``context_args``) whose
live result is fetched at run time and injected into context. Only that
owner-chosen tool auto-runs - arbitrary calls remain owner-invoked from
Agent Controls, so side effects stay behind the human gate. Fetch failures
degrade to phase-1 awareness, never break a turn.
"""

import asyncio
import json
import logging

from backend.services.platform_flags import flag_enabled

logger = logging.getLogger(__name__)

_SERVER_CAP = 10
_CONTEXT_TOOL_CAP = 2
_CONTEXT_RESULT_CHARS = 1500
_CONTEXT_TOOL_TIMEOUT = 6.0


def kb_entries(db, client_id: str) -> list[dict]:
    """KbEntry rows describing available MCP servers ([] when off/none)."""
    if not flag_enabled("os_mcp_enabled"):
        return []
    try:
        rows = (
            db.table("tenant_mcp_servers")
            .select("name, url, enabled")
            .eq("tenant_id", client_id)
            .eq("enabled", True)
            .limit(_SERVER_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_mcp_context: server read failed tenant=%s", client_id, exc_info=True
        )
        return []
    return _awareness_entries(rows)


def _awareness_entries(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    names = ", ".join(str(r.get("name") or "unnamed") for r in rows)
    return [
        {
            "topic": "connected external tools (MCP)",
            "answer": (
                f"This business has {len(rows)} external MCP tool server(s) "
                f"connected: {names}. When a task would benefit from one "
                "(looking up records, fetching documents, querying an external "
                "system), say so in your reply and name the server - the owner "
                "runs the tool from Agent Controls and shares the result. Do "
                "not claim to have called these tools yourself."
            ),
        }
    ]


def _render_result(result) -> str:
    """Flatten an MCP tool result to a short text snippet."""
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            texts = [
                str(block.get("text") or "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            if texts:
                return "\n".join(texts)[:_CONTEXT_RESULT_CHARS]
        try:
            return json.dumps(result)[:_CONTEXT_RESULT_CHARS]
        except (TypeError, ValueError):
            return str(result)[:_CONTEXT_RESULT_CHARS]
    return str(result)[:_CONTEXT_RESULT_CHARS]


async def tool_context_entries(db, client_id: str) -> list[dict]:
    """Live results of owner-designated read-only context tools ([] on any
    failure - a dead server degrades to phase-1 awareness, never breaks a
    turn)."""
    if not flag_enabled("os_mcp_enabled"):
        return []
    try:
        rows = (
            db.table("tenant_mcp_servers")
            .select("name, url, auth_header, auth_token, context_tool, context_args")
            .eq("tenant_id", client_id)
            .eq("enabled", True)
            .not_.is_("context_tool", "null")
            .limit(_CONTEXT_TOOL_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_mcp_context: context-tool read failed tenant=%s",
            client_id,
            exc_info=True,
        )
        return []

    entries: list[dict] = []
    for row in rows:
        tool = (row.get("context_tool") or "").strip()
        if not tool:
            continue
        server_name = str(row.get("name") or "unnamed")
        try:
            from backend.services import mcp_client

            args = row.get("context_args")
            result = await asyncio.wait_for(
                mcp_client.call_tool(
                    row["url"],
                    tool,
                    args if isinstance(args, dict) else {},
                    row.get("auth_header"),
                    row.get("auth_token"),
                ),
                timeout=_CONTEXT_TOOL_TIMEOUT,
            )
        except Exception:
            logger.warning(
                "os_mcp_context: context tool failed server=%s tool=%s tenant=%s",
                server_name,
                tool,
                client_id,
            )
            continue
        snippet = _render_result(result)
        if not snippet.strip():
            continue
        entries.append(
            {
                "topic": f"live data from {server_name} ({tool})",
                "answer": (
                    f"Fresh result from the owner-approved read-only tool "
                    f"'{tool}' on the {server_name} MCP server: {snippet}"
                ),
            }
        )
    return entries
