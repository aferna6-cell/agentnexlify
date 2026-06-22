---
type: source
source_id: connector-github-issues
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: 2026-06-22
sensitivity: normal
tags: [source, connector]
---

# Source: GitHub issues/PRs (smoke pass)

## What this is
Read-only smoke pass over `aferna6-cell/agentnexlify` open issues (84 open) + open PRs,
2026-06-22. See [[SOURCE-MANIFEST]] for connector verification.

## What it proves
- **Autonomous dev operation**: daily `morning-digest`, `nightly-commit-review`, and a
  `subconscious` improvement loop (numbered runs) auto-file issues and land fixes.
- **Plan display names**: `chatbot` = "AI Front Desk" ($19.99), `agent_os` = "AI Workforce"
  ($99.99). Confirmed in ToS rewrite (#330) + repricing PRs (#288, #291).
- **Live open loops** (2026-06-22): #263 (24 pending migrations, CRITICAL), #329 (apply
  migration 154 to prod), #330 (legal ToS review), #266 (secret encryption backfill), #325/
  #327/#328 (checkout/billing/retention), #286 (Agent OS alerts), PR #333 (51-commit
  main-pending batch, stale).
- **Recently fixed**: #308 webhook idempotency (revenue bug), #292/#293 stale plan names.
- **KB embeddings broken** since ~2026-04-30 (missing `VOYAGE_API_KEY` + Supabase MCP auth in cron).
