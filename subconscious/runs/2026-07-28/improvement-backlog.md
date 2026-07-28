# Improvement Backlog — Run 101 (2026-07-28)

## Winner (Run 101)
**`feature-docs-trio` SKILL.md** — create `.claude/skills/feature-docs-trio/SKILL.md` + update `feature-build/SKILL.md`. Autonomous-executable via nightly. Evidence: 3 occurrences in 7 days.

## Near-term (Run 102 carry-forward candidates)

### Step 9G CORRECTED — CCR Routine health monitor
- **What**: Add Step 9G to nightly SKILL.md: if KB stale >7 days AND no KB PR (opened by CCR) in 48h, comment on GH #403 "CCR Routine may be stalled"
- **Why**: Original Step 9G (run 100 winner) is obsolete — CCR Routine now handles KB autopopulate, GH Actions broken (#500). Monitoring gap: CCR creates PRs but nightly can't verify CCR is alive without a PR check.
- **Complexity**: Medium (requires `gh pr list --search` + timestamp comparison + correct alert text)
- **Risk**: False positive — CCR running but PRs unmerged would look like CCR stalled. Design: distinguish "0 PRs in 48h" from "N PRs open unmerged."
- **Mandate**: Run 101 mandate closes with Step 9G OBSOLETE marked in governance. Corrected Step 9G becomes run 102 candidate.

### Silent-green tenant heartbeat
- **What**: Nightly Step 9H — query conversations table for paid tenants with 0 conversations in 7 days. Create GH issue if found.
- **Why**: Keys Koffee widget failure ran 5+ weeks undetected. Booking CTA plain text (money path) ran without error. Bug-patterns.md explicitly calls for heartbeat prevention.
- **Prerequisite**: Verify SUPABASE_URL + SUPABASE_SERVICE_KEY available in nightly bash environment (cloud Routine vs script). Design dedup: don't re-alert within 7 days on same tenant.
- **Schema note**: Use `conversations.client_id` NOT `tenant_id` (critical invariant)
- **Priority**: HIGH customer impact. LOW implementation readiness until prerequisite verified.

## Medium-term

### `widget-ai-marker-add` SKILL.md
- **What**: Create skill for adding new LLM-triggered UI action markers (SHOW_BOOKING_PANEL class)
- **Evidence**: 2 occurrences (HANDOFF_REQUESTED historical, SHOW_BOOKING_PANEL e9b4972 2026-07-23)
- **Frequency**: ~1×/month
- **Value**: Prevents byte-identical sync skip (widget broken on tenant sites), strip-before-render skip (marker visible in chat)
- **Priority**: MEDIUM. Lower frequency than feature-docs-trio. Higher per-occurrence risk.

### `round-iteration-loop` SKILL.md
- **What**: Create skill for iterative Agent OS-style refinement rounds (TDD → implement → metrics → audit update)
- **Evidence**: 3 occurrences in 7 days (Rounds 6, 7, 8 of Agent OS)
- **Frequency**: ~3×/week during active Agent OS iteration
- **Value**: Round number from `ls backend/tests/test_suite_round*.py | wc -l` + 1 prevents round mislabeling; fake_supabase check prevents duplicate helper creation
- **Priority**: LOW until agent graph runtime is armed and Round N iteration resumes

## Closed / Obsolete

### Step 9G (original) — OBSOLETE as of 2026-07-28
- **Was**: `gh workflow run kb-autopopulate.yml` when KB stale > 7 days
- **Why closed**: CCR Routine ("KB Auto-Populate (CCR)") deployed 2026-07-23 handles this via cloud Routine without GH Actions secrets. GH Actions broken repo-wide (#500). Implementing original Step 9G would produce incorrect diagnostic.
- **Status**: Marked obsolete in governance.json run 101.

### Step 9F — IMPLEMENTED (run 99)
### Appointment completion carry-forward — superseded by nightly execution limitation (nightly can't create new service files)
### Widget drift topic — RETIRED permanently (runs 65-70, 6 consecutive failures)
