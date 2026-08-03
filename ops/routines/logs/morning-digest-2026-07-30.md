# Morning Digest — 2026-07-30

Generated: 2026-07-30 UTC

---

## Commits (last 24h)

- `ee0ca98` ops: nightly-commit-review 2026-07-30 [auto-nightly]
- `d68cdf6` ops: morning-digest 2026-07-29

2 commits. Ops logs only. No code landed.

---

## Issues (opened/updated last 24h)

### NEW — #610 Monitoring: paying tenant silence detection [HUMAN ACTION REQUIRED, revenue]
- Filed by subconscious run today
- 1 of 3 paying tenants was silent 5+ weeks before anyone noticed (Keys Koffee)
- SQL ready, needs wiring to Supabase scheduled function or GH Actions cron
- **Do this yourself — Supabase MCP unavailable in headless sessions**
- Option A (recommended): Supabase Dashboard → Database → Scheduled jobs → paste SQL from issue body
- Option B: GH Actions cron `monitor-tenant-silence.yml` — blocked until spending limit fixed

### CLOSED — #605 Autonomy run stranded in `running` forever
- Closed 2026-07-29 by #608 (sweeper implementation)
- 15 tests added, CI PASS

### OPEN — #609 Morning digest 2026-07-29 [digest] — no action needed

---

## Open PRs Needing Action

| # | Title | Age | Note |
|---|-------|-----|------|
| #611 | subconscious: run 2026-07-30 — Step 9H GH Actions CI systematic failure alerter | 0d | NEW today — review |
| #577 | subconscious: Step 9G + 9H KB self-healing + Actions heartbeat | 6d | **KB threshold HIT today — merge ASAP** |
| #606 | subconscious: run 101 — feature-docs-trio SKILL.md | 2d | DRAFT, low urgency |
| #604 | deps: lift the fastapi <0.136 cap | 2d | prereq done, safe to merge |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 6d | Do NOT apply migration 188 yet |
| #596–#598, #594–#595 | Dependabot | 2d | Queue after GH Actions restored; #596 superseded by #604 |

All CI red — GH Actions spending limit (issue #500, **DAY 10**). Not PRs' fault.

---

## Subconscious Recommendation

**Run 100 winner (Step 9G):** trigger `kb-autopopulate.yml` when KB stale >7d, diagnostic comment on #403 if secrets fail. KB crossed 7-day threshold **today** (last compile: 2026-07-23). Step 9G is in PR #577 — merge fires the fix.

**Run today (Step 9H, PR #611):** GH Actions CI systematic failure alerter — new nightly check for chronic CI failures, surface to #500 instead of silently red.

---

## KB Health

- Last compile: 2026-07-23 (7 days ago)
- 7-day stale threshold: **HIT TODAY**
- 124 articles indexed
- Step 9G (PR #577) auto-triggers repair — **merge now**
- Embeddings still deferred (VOYAGE_API_KEY owner-gated); FTS fallback active

---

## Top 3 Priorities Today

### 1. FIX GH ACTIONS SPENDING LIMIT [BLOCKER — owner only, DAY 10]
- `github.com/settings/billing/summary` → raise spending limit or fix payment
- Blocks: ALL CI, PR validation, monitoring, KB autopopulate, nightly loops, dependabot merges
- Step 9H (PR #611) will alert on this daily once merged — but CI must be restored first
- Issue: #500

### 2. MERGE #577 — KB Self-Healing [**THRESHOLD HIT TODAY**]
- KB is 7 days stale as of today
- PR is SKILL.md only — no code — safe to merge even without CI
- Step 9G fires `gh workflow run kb-autopopulate.yml` immediately on merge
- Without this: AI chat quality degrades for all 3 paying tenants

### 3. WIRE PAYING TENANT SILENCE ALERT [#610 — revenue protection]
- 1 in 3 tenants was silent 5+ weeks undetected
- SQL ready in issue #610 body — 5 min to wire in Supabase Dashboard
- Supabase Dashboard → Database → Scheduled jobs → paste SQL → daily at 9am
- Prevents next silent churn event

---

_Nightly review: CLEAN (2 commits, ops logs only, 0 bugs, 0 issues filed)_
_Log: `ops/routines/logs/morning-digest-2026-07-30.md`_
