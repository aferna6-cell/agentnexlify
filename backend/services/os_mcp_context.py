"""MCP tool awareness for Agent OS runs (suite item 3 — interop phase 2).

Injects the tenant's enabled MCP servers into SharedContext.kb so every
department KNOWS what external tools exist and proposes their use in
deliverables ("I can pull this from your crm server - run it from Agent
Controls"). Actual tool calls stay owner-invoked (/api/v1/os/mcp) so
propose-only holds; no network calls happen on the turn path - this is a
deterministic single-table read, cached per turn by the caller.
"""

import logging

from backend.services.platform_flags import flag_enabled

logger = logging.getLogger(__name__)

_SERVER_CAP = 10


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
