---
name: mcp-builder
description: Build or debug MCP servers that expose external services (Railway, Twilio, Resend, custom) as Claude tools. Load when user says "add MCP server", "build an MCP for X", "FastMCP server", "new MCP tool", or when extending .mcp.json entries beyond existing supabase.
origin: https://github.com/anthropics/skills/tree/main/skills/mcp-builder
version: 1.0.0
triggers:
  - add MCP server
  - build an MCP
  - FastMCP server
  - new MCP tool
  - wire up MCP
  - extend .mcp.json
---

# MCP Builder — FastMCP Server Development

Adapted from anthropics/skills. Our stack is Python, so default to FastMCP.

## When to Use
- Building a new MCP server for Railway / Twilio / Resend / custom internal tool
- Debugging existing MCP server connection or tool registration
- Extending `.mcp.json` with a new entry
- Designing the tool surface area for a newly wired external service

## When NOT to Use
- Simple HTTP API calls that don't need MCP abstraction
- Calling existing MCPs (just invoke them — don't re-build)
- OAuth-only integrations where a plain Python client suffices

Adapted from anthropics/skills. Our stack is Python, so default to FastMCP.

## Four-phase workflow

1. **Discover** — identify the external service, list its core capabilities, pick 5-10 real user tasks the MCP must support.
2. **Design tools** — one tool per task. Names: verb + noun (`send_sms`, `list_invoices`). Each tool has: description (≤200 chars), typed params, return shape.
3. **Implement** — FastMCP Python server: `@mcp.tool()` decorators, pydantic models for args/returns, context injection for auth.
4. **Eval** — write 5-10 sample prompts per tool, run with the server loaded, score accuracy/coverage/error-handling.

## Quality bars
- Tool descriptions drive trigger accuracy — specific + task-oriented wins.
- Return structured data (dicts/pydantic), not free text.
- Error messages must be actionable, not just HTTP codes.
- One tool per real task, not per API endpoint.
- Test with realistic prompts, not just unit tests.

## AgentNexLiFy MCP inventory
- **Active**: supabase (stdio via `.mcp.example.json`; token via `SUPABASE_ACCESS_TOKEN` env)
- **Plugin-provided**: context7, playwright, deepwiki (see `.claude/settings.json.enabledPlugins`)
- **Candidates for future**: Twilio (SMS send/receive), Resend (email send/thread), Railway (deploy status), Stripe (subscription ops)

## File layout for new MCP
```
backend/mcp-servers/<name>/
├── server.py       # FastMCP app + @mcp.tool defs
├── requirements.txt
└── README.md       # 3-tool minimum + eval prompts
```

## Full upstream skill
https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md (236 lines — full four-phase detail + FastMCP examples)
