---
type: source
source_id: connector-github-issues
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: 2026-07-23
last_refresh: 2026-07-23T14:38Z
sensitivity: normal
tags: [source, connector]
---

# Source: GitHub issues/PRs (auto-refreshed)

## What this is
Live snapshot from `refresh_connectors.py` of `aferna6-cell/agentnexlify`.

## Counts (as of 2026-07-23T14:38Z)
- Open issues: 25
- Open PRs: 0
- Recent closed issues sampled: 30

## Top open issues (non-digest)
  - #567 migration 187: add RLS policy to pending_automations + re-cut activity_feed_events view
  - #536 ops: provision INTEGRATIONS_ENC_KEY in Railway before applying migration 176
  - #500 GitHub Actions down repo-wide: all hosted-runner jobs fail in 3s since 12:21 UTC — check Actions billing/spending limit [human-action-required]
  - #484 Agent OS loop health -- 2026-07-20
  - #451 Implement review_responder.post_response_stub once GBP OAuth credentials land
  - #403 Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate [human-action-required]
  - #399 autopilot-issue-loop GitHub Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired [CRITICAL]
  - #394 Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing [MEDIUM]
  - #265 deps: re-raise the fastapi &lt;0.136 cap once starlette is bumped to a 0.50-compatible release
  - #193 [subconscious] Moratorium active: 13 pending items, oldest 44 days
  - #114 [ops-automation] Migration 118 — ops_automation_v1 schema (missed_call_texts, appointments, pending_automations, materialized view, RLS)
  - #70 [memory-hygiene] KB article provenance — source URL + last_validated + stale warnings
  - #69 [memory-hygiene] Widget conversation memory tier — relevance + confidence scoring
  - #64 [zapier] Epic — Zapier CRM Export (new_lead trigger)
  - #63 [zapier] v1.1 — OAuth + dynamic custom field introspection (post-GA)

## Notes
- Autonomous-dev cadence: morning-digest / nightly-commit-review / subconscious loop.
- Regenerated automatically; edits here will be overwritten on next refresh.
