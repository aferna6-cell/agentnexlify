# Owner-Facing MCP Server (/mcp)

Finished 2026-07-22 (round 7 item 4). `backend/mcp_server.py` had existed
since migration 041 but was never mounted, and the setup page showed the
widget key - the connect flow could not work end to end.

## Architecture

- `backend/mcp_server.py` - FastMCP server, 6 read/reply tools over the
  tenant's leads, appointments, conversations, action items, analytics.
  `stateless_http=True` (prod runs 4 uvicorn workers, no session
  affinity), `streamable_http_path="/"`.
- `backend/main.py` mounts it at `/mcp` and runs
  `mcp.session_manager.run()` inside the app lifespan.
- Auth: per-tenant `mcp_` key (tenants.mcp_api_key + mcp_enabled,
  migration 041). Each tool takes an optional `api_key` argument and
  falls back to the `Authorization: Bearer` (or `X-API-Key`) header of
  the HTTP request - the header is what the shipped config uses.

## Key management

- `GET /api/v1/auth/mcp-key/{tenant_id}` - read key state (owner role).
- `POST /api/v1/auth/mcp-key/{tenant_id}` - generate/rotate. Gated by
  `require_agent_os_access` (agent_os + grandfathered plans; 402 upsell
  payload otherwise).
- `DELETE /api/v1/auth/mcp-key/{tenant_id}` - revoke (clears key,
  disables mcp_enabled).

## Owner connect flow (what MCPSetupPage renders)

1. Dashboard -> MCP Setup -> Generate MCP key.
2. Copy the generated Claude Desktop config:

```json
{
  "mcpServers": {
    "agentnexlify": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://agentnexlify-production.up.railway.app/mcp",
        "--header", "Authorization: Bearer mcp_..."
      ]
    }
  }
}
```

3. Restart Claude Desktop; the six agentnexlify tools appear. No key
   pasting in conversations - mcp-remote sends the header on every call.

## Gotchas

- The mount is a Starlette sub-app: it bypasses FastAPI middleware
  ordering but still sits behind the CORS middleware. Tools return
  plain-text errors (not exceptions) on bad keys by design - assistants
  surface them readably.
- Revoking or regenerating the key kills existing connections on their
  next call (key checked per request; nothing cached).
- `python -m backend.mcp_server` still runs stdio mode for local tests.
