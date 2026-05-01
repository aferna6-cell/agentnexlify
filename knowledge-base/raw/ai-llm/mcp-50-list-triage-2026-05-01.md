# MCP/Connector 50-List Triage — 2026-05-01

**Source:** Khairallah listicle "50 Claude integrations that actually transform your workflow."
**Decision:** ~80% redundant with existing AgentNexLiFy stack. 3 net-new candidates evaluated. 2 documented as install-on-demand. 1 scaffolded as template.

---

## Already wired (skip — no action needed)

| Item from list | Already in stack | Source |
|---|---|---|
| Gmail, Google Calendar, Google Drive | Built-in connectors enabled | Claude Desktop |
| Slack | `slack` plugin + MCP | `.claude/plugins` |
| Notion | `.mcp.json` HTTP MCP | `.mcp.json:52-55` |
| Microsoft 365, OneDrive, SharePoint | Built-in connectors | Claude Desktop |
| Tavily | `.mcp.json` stdio | `.mcp.json:93-100` |
| Context7 | `.mcp.json` + `context7` plugin | `.mcp.json:35-38` |
| GitHub MCP | `gh` CLI + `github` plugin | `.claude/plugins` |
| Supabase MCP | `.mcp.json` with project-ref | `.mcp.json:3-15` |
| Linear | `linear` plugin (low-priority) | `.claude/plugins` |
| Sentry | `sentry` plugin | `.claude/plugins` |
| HubSpot | `marketing.hubspot` plugin | `.claude/plugins` |
| Vercel | `vercel` plugin + skills | `.claude/plugins` |
| Playwright | `.mcp.json` stdio | `.mcp.json:39-42` |
| Firecrawl | `.mcp.json` + `firecrawl` plugin | `.mcp.json:85-92` |
| Apify | `.mcp.json` stdio | `.mcp.json:69-76` |
| ElevenLabs | `.mcp.json` (uvx) | `.mcp.json:77-84` |
| Browserbase | `.mcp.json` stdio | `.mcp.json:60-68` |
| Stripe | `stripe` plugin | `.claude/plugins` |
| Amplitude | `amplitude` plugin (low-priority) | `.claude/plugins` |
| Exa | `.mcp.json` stdio | `.mcp.json:101-108` |
| Sequential Thinking | MCP server | `mcp__sequential-thinking__*` |
| Memory | MCP server | `mcp__memory__*` |
| Chrome DevTools | `chrome-devtools-mcp` plugin | `.claude/plugins` |
| Mintlify | `mintlify` plugin (low-priority) | `.claude/plugins` |

**Verdict:** ~30/50 redundant. List is generic awareness piece, not gap analysis.

---

## Rejected (don't install — better alternative exists)

| Item | Reason rejected |
|---|---|
| Task Master AI | `prd-to-issues` skill + `issue-to-pr-loop` cover this. Task Master adds nothing on top of GH issues. |
| Postgres MCP (read-only) | Supabase MCP covers Postgres queries. RLS-aware via project token. |
| Markdownify MCP | `pdftotext` rule + `agent-browser` cover PDF/web. Already documented in `.claude/rules/pdf-handling.md`. |
| Codebase Memory MCP | Duplicates `~/.claude/projects/-home-aidan-agentnexlify/memory/` + knowledge-base pgvector. |
| Stealth Browser MCP | Browserbase + Playwright cover automation. Stealth needs are project-specific; revisit if blocked. |
| Mixpanel MCP | Amplitude already wired (low-priority). No need for second analytics. |
| BigQuery / Snowflake / MongoDB MCP | No data warehouse / NoSQL workload. Postgres via Supabase is canonical. |
| Airtable MCP | No Airtable usage in stack. |
| Discord / Telegram / Teams MCP | No team comms workflow on these platforms. |
| Intercom / Zendesk MCP | Widget IS the support layer. No CS platform integration needed. |
| Salesforce MCP | HubSpot is partner CRM. No Salesforce. |
| Docker / AWS / Cloudflare / GitLab MCP | Railway + Vercel + GitHub = stack. AWS partial via deploy-on-aws plugin. |
| Google Analytics MCP | No GA4 instrumentation. Amplitude covers product analytics. |
| Excel MCP | xlsx skill (built-in) covers Excel parsing without an MCP server. |
| Dropbox / Box MCP | No Dropbox/Box usage. Drive + OneDrive cover cloud storage. |

---

## Net-new candidates evaluated

### #1 Twilio MCP — DOCUMENTED, NOT YET INSTALLED

**Why relevant:** Twilio is core to widget appointment booking + SMS follow-up. Existing code in `backend/services/twilio_*.py` is the integration. No MCP server wired for debugging call/SMS flows.

**Install procedure** (run when ready):
```bash
# 1. Verify package on npm
npm view @twilio-alpha/mcp 2>/dev/null || npm view twilio-mcp

# 2. Add to .mcp.json (replace <PACKAGE> with verified name)
# Example block (DO NOT paste blindly — verify package first):
#  "twilio": {
#    "type": "stdio",
#    "command": "npx",
#    "args": ["-y", "<PACKAGE>"],
#    "env": {
#      "TWILIO_ACCOUNT_SID": "${TWILIO_ACCOUNT_SID}",
#      "TWILIO_API_KEY":     "${TWILIO_API_KEY}",
#      "TWILIO_API_SECRET":  "${TWILIO_API_SECRET}"
#    }
#  }

# 3. Verify env vars exist
grep -E "TWILIO_(ACCOUNT_SID|API_KEY|API_SECRET)" .env

# 4. Restart Claude Code session
```

**Capability vs current stack:** Backend services already call Twilio API directly. MCP server would add session-level read access (call logs, SMS history, message status) for live debugging without writing one-off Python.

**Open question:** Confirm official Twilio MCP package name. As of training cutoff, `@twilio-alpha/mcp` is the candidate but unverified. User confirms before adding to `.mcp.json`.

### #4 MCPHub — DOCUMENTED, NOT YET INSTALLED

**Why relevant:** Project has 15+ MCP servers in `.mcp.json` + 30+ plugin-provided MCPs. Context bloat is a real cost. MCPHub manages multiple MCPs via HTTP gateway, lazy-loading tool schemas.

**Tradeoff:** Adds routing layer = new failure mode. Only worth it if MCP context bloat becomes load-bearing on session quality. Currently `ToolSearch` + deferred-tool architecture covers this gap.

**Install procedure** (run only if MCP sprawl hurts):
```bash
# Candidates (verify first):
#   samanhappy/mcphub  — most-starred fork
#   @mcphub/mcp        — alternative

# 1. Verify
npm view mcphub 2>/dev/null

# 2. Run as gateway, point .mcp.json entries at HTTP transport instead of stdio
```

**Verdict:** Defer. Current `ToolSearch` deferred-tool pattern + `disabled: true` flags in `.mcp.json` are sufficient. Re-evaluate if total MCP count exceeds 25.

### #5 FastMCP — TEMPLATE SCAFFOLDED

**Path:** `mcp-servers/example-fastmcp/`
**Files created:**
- `server.py` — minimal FastMCP server with one tool + one resource
- `pyproject.toml` — fastmcp dep
- `README.md` — wire-into-mcp.json instructions

**When to extend:** Project-specific MCP for tenant-aware operations no public MCP covers. Examples:
- `tenant_health` tool (one-call activity feed snapshot for a client_id)
- `widget_diff` tool (compare `widget/` vs `frontend/public/widget/` byte-identical check)
- `migration_next` tool (next free migration number + drift check)

Wire via:
```json
"agentnexlify-internal": {
  "type": "stdio",
  "command": "uv",
  "args": ["run", "--project", "mcp-servers/example-fastmcp", "python", "server.py"]
}
```

---

## Decisions locked
- **Don't install** Task Master AI, Postgres MCP, Codebase Memory MCP, Markdownify, Mixpanel — better alternatives in stack
- **Don't install** any data warehouse / NoSQL / partner CRM MCPs — no workload
- **Future install candidate** Twilio MCP — verify package name + creds first
- **Defer** MCPHub — current deferred-tool pattern sufficient
- **Template ready** FastMCP scaffold — extend when tenant-specific MCP need arises

## Cross-refs
- `.claude/rules/plugins.md` — full routing decisions
- `.mcp.json` — current MCP server config
- `mcp-servers/example-fastmcp/` — FastMCP template
- `~/.claude/plugins/installed_plugins.json` — plugin install state

## Context
50-list shared 2026-05-01 by Khairallah on social. Triaged in this session. Outcome: list is generic awareness, not gap analysis. ~80% redundant. Keep this article so future sessions skip re-triage if list re-shared.
