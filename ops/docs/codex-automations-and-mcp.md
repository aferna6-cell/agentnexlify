# Codex Automations And MCP

This note records the Codex app automations that support AgentNexLiFy and the local MCP setup expected for deeper repo work.

## Active Codex Automations

- Morning Market Radar: daily morning scan of public social/news sources for AgentNexLiFy-relevant market, AI-agent, real-estate tech, and platform signals.
- Competitor Watch: weekly scan for AI real-estate chatbot, CRM automation, lead qualification, pricing, positioning, and launch changes.
- Widget Canary Review: weekday production widget/browser canary that reports only meaningful UX, CORS, console, latency, or API-path issues.
- Conversation Quality Sampler: twice-weekly review of conversation-quality signals, missed qualification, weak handoffs, and prompt/product fixes.
- Platform Release Scout: weekly review of official release notes and status/changelog sources for Anthropic, Supabase, Vercel, Railway, Twilio, Resend, Stripe, and key framework/tooling dependencies.
- Agent System Drift Check: weekly check for stale agent-system references, broken skill metadata, routing drift, and manifest/doc mismatches.

## Supabase MCP Setup

The repo already includes `.mcp.example.json` with a read-only Supabase MCP server definition. To enable it locally:

1. Create a Supabase personal access token from the Supabase dashboard.
2. Copy `.mcp.example.json` to `.mcp.json`.
3. Set `SUPABASE_ACCESS_TOKEN` in the shell or user environment. Do not commit the token.
4. Restart the agent runtime so it discovers the MCP server.

PowerShell session example:

```powershell
Copy-Item .mcp.example.json .mcp.json
$env:SUPABASE_ACCESS_TOKEN = "sbp_your_personal_access_token"
```

Persistent Windows user environment example:

```powershell
[Environment]::SetEnvironmentVariable("SUPABASE_ACCESS_TOKEN", "sbp_your_personal_access_token", "User")
```

Keep this MCP read-only by default. Use migration files and the normal Supabase workflow for schema/data changes unless a task explicitly calls for write access.
