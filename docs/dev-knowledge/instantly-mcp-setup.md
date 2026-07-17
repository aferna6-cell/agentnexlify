# Instantly MCP — Setup

Cold-email platform (instantly.ai) MCP server. Gives Claude tools for campaigns, analytics, leads, and email accounts via the Instantly v2 API.

## Server
- Package: [`instantly-mcp`](https://www.npmjs.com/package/instantly-mcp) (community, v1.0.5 as of 2026-07-17)
- Auth: Instantly v2 API key (Settings → Integrations → API in the Instantly dashboard)

## Install (local `.mcp.json` — gitignored, line 45 of `.gitignore`)
Add to `.mcp.json` at repo root:

```json
{
  "mcpServers": {
    "instantly": {
      "command": "npx",
      "args": ["-y", "instantly-mcp"],
      "env": {
        "INSTANTLY_API_KEY": "<your Instantly v2 API key>"
      }
    }
  }
}
```

Restart Claude Code after adding — MCP servers are loaded at session start (`one-task-one-chat.md` cache hygiene: never add MCP mid-session).

## Security
- `.mcp.json` is gitignored — the key stays local. Never move this entry into a committed file (CLAUDE.md invariant 7: secrets never in commits).
- The v2 key is a base64 string scoped to the whole workspace. Rotate it in the Instantly dashboard if it was ever pasted into a chat, log, or ticket.

## No-MCP fallback (works today, any session)
The v2 API is plain REST with a Bearer token:

```bash
curl -H "Authorization: Bearer $INSTANTLY_API_KEY" \
  "https://api.instantly.ai/api/v2/campaigns"           # list campaigns
curl -H "Authorization: Bearer $INSTANTLY_API_KEY" \
  "https://api.instantly.ai/api/v2/campaigns/analytics"  # per-campaign stats
```

Campaign `status` codes: `0` draft · `1` active · `2` paused · `3` completed · `-1` deleted/archived draft · `-2` bounce-protect · `-99` suspended.

## Cross-refs
- `.claude/rules/plugins.md` — MCP triage decisions
- `.claude/skills/email-sequence/SKILL.md` — campaign design patterns
