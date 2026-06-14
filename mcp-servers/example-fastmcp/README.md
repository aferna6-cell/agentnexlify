# AgentNexLiFy Internal MCP — FastMCP Template

Project-specific MCP server. Extend with tools that no public MCP covers.

## What's here

Two example tools + one resource demonstrating the pattern:

- `widget_diff()` — check `widget/` vs `frontend/public/widget/` byte-identical invariant
- `migration_next()` — return next free migration number
- `agentnexlify://stack-info` — static stack reference resource

## Install + smoke test

```bash
cd mcp-servers/example-fastmcp
uv sync
uv run python server.py  # runs MCP server on stdio
```

## Wire into .mcp.json

Add to `/home/aidan/agentnexlify/.mcp.json`:

```json
"agentnexlify-internal": {
  "type": "stdio",
  "command": "uv",
  "args": [
    "run",
    "--project",
    "mcp-servers/example-fastmcp",
    "python",
    "server.py"
  ]
}
```

Restart Claude Code. Verify tools appear via `mcp__agentnexlify-internal__*` namespace.

## When to extend this

Add a tool here ONLY when:
1. No public MCP covers the operation
2. Operation is project-specific (touches AgentNexLiFy invariants)
3. Operation benefits from being callable mid-session vs running a Python one-off

Candidate tools (not yet implemented):
- `tenant_health(client_id)` — one-call activity feed snapshot
- `kb_compile_check()` — verify knowledge-base/raw → wiki compile readiness
- `migration_apply_dry(migration_number)` — preview migration without applying
- `stripe_plan_lookup(client_id)` — verify subscription plan vs feature gates

## When NOT to add a tool here

- Tool is generic (it belongs in a public MCP — find or build separately)
- Tool only used once (just write a Python script)
- Tool is destructive without confirmation (route through backend with explicit auth)

## License

Private — AgentNexLiFy internal use.
