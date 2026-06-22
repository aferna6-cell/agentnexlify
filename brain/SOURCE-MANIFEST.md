---
type: manifest
date: 2026-06-22
phase: orientation
---

# Source Manifest

Connector verification (Connector Verification Gate) + local source inventory.
All connector checks below were **read-only identity verifications**. No data was
ingested and no external writes/mutations were performed.

## Connector Verification

### GitHub — ✅ smoke-pass ingested
- Connector: GitHub MCP (`mcp__github__*`)
- Account / user ID: `aferna6-cell` (id `228568372`)
- Workspace/org/team: n/a (personal account; 30 public repos)
- Verification method: `get_me`; smoke pass `list_issues` + `list_pull_requests` on
  `aferna6-cell/agentnexlify`
- Timestamp: 2026-06-22
- Capability observed: read (profile, 84 open issues, open PRs)
- Approved for ingestion: **yes (read, business scope)** — smoke pass done →
  [[connector-github-issues]]. Broader history pending Hard Checkpoint 2.

### Vercel — ✅ verified
- Connector: Vercel MCP
- Account: team `aferna6-cell's projects`
- Team ID: `team_nKtxgUlI3JosDKSTsOs3yF96`
- Verification method: `list_teams`
- Timestamp: 2026-06-22
- Capability observed: read (teams)
- Approved for ingestion: **not yet** (low priority; deploy metadata only)

### Supabase — ✅ verified
- Connector: Supabase MCP
- Account/org: `VoltOps` (org id `jsymlqyawvukrxtcoiqz`)
- Projects: `aferna6-cell's Project` (`pxserpybmajixqrmzaly`, ACTIVE_HEALTHY) ·
  `agentnexlify-os-demo` (`oqmnnloktcwqeicnkqcy`, INACTIVE) ·
  `BetBrain` (`qmlrecmgmqniitkplpqv`, INACTIVE)
- Verification method: `list_organizations`, `list_projects`
- Timestamp: 2026-06-22
- Capability observed: read (org/project metadata; `list_tables` on active project — ~130
  tables, RLS on all)
- Approved for ingestion: **yes (read schema, business scope)** — smoke pass done →
  [[connector-supabase-schema]]. Broader/data reads pending Hard Checkpoint 2.

### Slack — ✅ verified
- Connector: Slack MCP
- Account: `aidanfernandes31@gmail.com` (user id `U0AU23Y8PSN`)
- Workspace: "Agent Nexlify"
- Verification method: `slack_read_user_profile`
- Timestamp: 2026-06-22
- Capability observed: read (own profile; `slack_search_channels` → none found)
- Approved for ingestion: **yes (read)** — smoke pass done → [[connector-slack]]. Workspace is
  effectively empty; low-value source, nothing to ingest now.

### Google Calendar — ⚠️ verified, identity divergence
- Connector: Google Calendar MCP
- Account: `aferna6@g.clemson.edu` (Clemson University student account)
- Calendars: US Holidays · "Active Brother Class Schedule" (fraternity) ·
  "LUCU EVENTS" (`lucu@g.clemson.edu`, campus ministry) · `aferna6@g.clemson.edu`
- Verification method: `list_calendars`
- Timestamp: 2026-06-22
- Capability observed: read (calendar list)
- Approved for ingestion: **BLOCKED — scope decision required** (school/personal vs business)

### Gmail — ⚠️ account address unconfirmed
- Connector: Gmail MCP
- Account: address not exposed by `list_labels`; user-defined label
  `afernandes@hamdenhall.org` present (+ legacy label "Moved 2023-05-17")
- Workspace: n/a
- Verification method: `list_labels`
- Timestamp: 2026-06-22
- Capability observed: read (labels)
- Approved for ingestion: **BLOCKED — confirm account address + scope first**

### Google Drive — ⛔ blocked
- Connector: Google Drive MCP
- Account: unknown (could not read)
- Verification method: `list_recent_files` → returned "MCP tool call requires approval"
- Timestamp: 2026-06-22
- Capability observed: **none — read denied at MCP layer**
- Approved for ingestion: **BLOCKED — requires user approval to read at all**

## Local Sources (filesystem — primary for Phase A)

| ID (proposed) | Path | Type | Sensitivity |
|---|---|---|---|
| repo-agentnexlify | `/home/user/agentnexlify` | git repo | normal |
| repo-agent-os | `/home/user/Agent-Nexlify-OS` | git repo | normal |
| kb-wiki | `agentnexlify/knowledge-base/wiki/` | compiled wiki (117 articles) | normal |
| dev-knowledge | `agentnexlify/docs/dev-knowledge/` | engineering notes | normal |
| eng-memory | `agentnexlify/docs/engineering-memory/` | session memory | normal |
| ai-memory | `agentnexlify/ai/memory/*.json` | structured memory | normal |
| planning | `agentnexlify/planning/` | decisions/specs/positioning | normal |
| specs-plans-audits | `agentnexlify/{specs,plans,audits}/` | feature docs | normal |

> Source traces under `Sources/` will cite these paths. Secrets must never be copied
> in (see redaction policy); `.env*` and credential files are out of scope for ingestion.
