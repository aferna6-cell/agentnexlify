# Nightly Review — 2026-09-05

Run started: 2026-09-05 (automated scheduled task)
Branch: main (was detached HEAD on start — auto-recovered to main + pulled)

## Commits reviewed (last 24h, no-merges)

- `9b1381b` fix(sms): meter sms_agent.reply with send-boundary idempotency (#799)
- `0b41f4d` fix(widget): meter widget_guard.screen with reserve/record/release (#798)
- `3b93367` fix(voice): meter call summaries and dedupe dual triggers (#797)
- `9de7f60` fix(widget): meter extract_tags with reserve/record/release (#796)
- `3e1a023` fix(widget): meter categorize_conversation with reserve/record/release (#794)
- `1d056f3` fix(widget): meter extract_action_items with reserve/record/release (#793)
- `bc0332b` fix(voice): meter live-AI respond with reserve/record/release (#792)
- `d20d0fd` fix(agent-system): count Windows git-symlink skill placeholders (#761)
- `43844a5` feat(schema): read-only schema-log vs live migration drift guard (#788)
- `d192888` ops: morning-digest 2026-09-04
- `f72a274` docs(schema): record 195/196/197 as applied on staging and prod
- `966acb4` fix(nightly): block_demo_role on website_connect POSTs + log parse errors [auto-nightly-2026-09-04]
- `cad5137` ops: nightly-commit-review 2026-09-04

Total: 13 commits

## Risk Classification

### MEDIUM — metering commits (#792–#799)
- `bc0332b`, `3e1a023`, `1d056f3`, `9de7f60`, `3b93367`, `0b41f4d`, `9b1381b` — AI usage guard reserve/record/release pattern across voice, widget, and SMS paths. All well-tested (each commit adds 600–1726 line test files). Complex production logic with intentional crash windows documented in code comments. No autonomous fix warranted.

### LOW — safe, reviewed
- `d20d0fd` — script-level Windows symlink fix, well-scoped tests. No bugs found.
- `43844a5` — new read-only drift check script, no FastAPI file, `from __future__ import annotations` is in a standalone script (not a FastAPI file — allowed). No bugs found.
- `d192888`, `f72a274`, `cad5137` — docs/ops log files. No bugs.
- `966acb4` — previous nightly auto-fix, correct.

## Findings

### Fixed autonomously (0)
No LOW-risk bugs found in the 24h commit window.

### Issues opened (1)
- [OPERATIONAL] #800 — Brain connector 44 days stale (last run 2026-07-23) → human-action-required

### Skipped (FORBIDDEN paths)
- None in this run.

## Extended checks

### 9A — Moratorium Status
`moratorium_active: false` — no escalation needed. 1 pending approval item (god-class-splitter on email_sequences.py, below 3-item threshold).

### 9B — Healthz Monitor
`ops/monitoring/healthz-alert.sh` present — monitoring active. Skip.

### 9C — Brain Connector Health
Consecutive failures: 0 (last entry 2026-07-23 shows github: ok, supabase: ok via CCR workaround).
Age gate: last success 2026-07-23, **44 days stale** (threshold: 14 days).
No existing open issue found for brain connector staleness.
**Action:** Created GH issue #800 with labels `human-action-required, brain-connector, operational`.

### 9D — Issue-to-PR Loop Health
Skipped (gh CLI not available in this environment; would need gh workflow run access).

### 9E — Credential Rotation
- AUTOPILOT_GH_TOKEN: last rotated 2026-07-04, 63 days ago (<76 threshold). OK.
- Brain connector GitHub PAT: last rotated 2026-07-04, 63 days ago. OK.
- SUPABASE_ACCESS_TOKEN: **unknown** (not yet set/tracked). No alert threshold computable.
Step 9E: 2 credentials checked, 0 approaching expiry (>=76 days), 1 unknown state (SUPABASE_ACCESS_TOKEN).

### 9F — KB Autopopulate Staleness
Last successful run: 2026-08-26 (10 days ago, threshold: 7 days).
**Action:** Comment posted on GH #403 alerting of 10-day staleness.

### 9G — KB Autopopulate Self-Healing
gh CLI not available in this remote environment. Cannot trigger `gh workflow run kb-autopopulate.yml`. Logged: Step 9G: gh workflow run not available — KB stale 10 days, see GH #403.

### 9I — Demo-Role Security Sweep
Scanned all backend/routers/ files with mutating routes (excluding known exceptions).
**Result: 0 violations — all routers have block_demo_role. PASS.**

### 9J — Dependabot Auto-Merge
19 open Dependabot PRs total.
Checked: #722 (eslint 10.7→10.9.1), #721 (@typescript-eslint/parser 8.64→8.68).
Both have `mergeable_state: unknown` (base has moved; last updated 2026-09-03, >48h).
**Action:** Triggered `@dependabot rebase` on #721 and #722 (rebase_trigger_count: 2).
Remaining 17 Dependabot PRs not individually checked this run (token budget).

Step 9J: 19 Dependabot PRs open, 0 merged, 17 skipped (not checked), 2 rebase-triggered (unknown state).

### 9K — Stale Subconscious PRs
1 open subconscious PR: #795 (subconscious: run 2026-09-04-pm, 1 day old).
total_count=1, stale_count=0 (>30d), critical_count=0 (>60d).
Under threshold of 3 stale — no action.
Step 9K: 1 subconscious PR open (0 stale, 0 critical).

## Next action
Brain connector 44 days stale → human must rotate GitHub PAT + set SUPABASE_ACCESS_TOKEN in Railway (GH #800).
KB autopopulate 10 days stale → check ANTHROPIC_API_KEY in GitHub Actions (GH #403).
17 remaining Dependabot PRs need CI status check on next run.
