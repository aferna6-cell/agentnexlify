# Improvement Backlog — Run 102 PM (2026-07-28)

## Winner (Run 102)
**`god-class-splitter` SKILL.md update** — add backward-compat re-export step + test patch target grep step. Both omissions caused immediate test failures on BOTH god-class splits this week. Evidence: `docs/skill-discovery/2026-07-27.md`, HIGH priority. XS effort.

**Bonus action:** Comment on PR #577 via GH MCP — Step 9G in that PR is obsolete (triggers `gh workflow run kb-autopopulate.yml` which is wrong with CCR Routine active + GH Actions broken #500).

## Near-term (Run 103 carry-forward candidates)

### Step 9G CORRECTED — CCR Routine health monitor
- **What**: Add corrected Step 9G to nightly SKILL.md: if KB stale >7 days AND no KB PR from CCR in 48h (`gh pr list --search "head:kb-autopopulate"` OR `gh pr list --search "kb autopopulate"`), comment on GH #403 "CCR Routine may be stalled"
- **Why**: AM run (run 101) confirmed original Step 9G obsolete. PR #577 contains stale version. Monitoring gap: CCR creates PRs but nightly has no way to verify CCR alive without a PR check.
- **Complexity**: Medium — `gh pr list` search semantics + timestamp comparison + distinguish 0 PRs from N PRs open unmerged (false positive risk)
- **Prerequisite**: KB must approach 7-day staleness threshold to create urgency; OR PR #577 revision is targeted
- **Priority**: Medium. KB healthy at 5 days (2026-07-23 last run).

### Silent-green tenant heartbeat (Step 9H)
- **What**: Nightly Step 9H — query `conversations` table for paid tenants (`agent_os` plan) with 0 conversations in 7 days. Create GH issue if found. Dedup: skip if same `client_id` (NOT `tenant_id`) already has open issue in last 7 days.
- **Why**: Keys Koffee widget failure ran 5+ weeks undetected. `bug-patterns.md` calls for heartbeat prevention explicitly.
- **Prerequisite**: Verify `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` available in nightly CCR bash environment. Design dedup logic.
- **Schema note**: `conversations.client_id` NOT `tenant_id` — critical invariant.
- **Priority**: HIGH customer impact. LOW implementation readiness until prerequisite verified.

### GH comment + `ai-ready` label on #605 (autonomy sweeper)
- **What**: Comment on #605 with root cause (crash mid-verify strands run in `running` state permanently, reproduced at cycle 7, no sweeper) + add `ai-ready` label
- **Why**: Prerequisite before safely arming the autonomous engineering Routine. Without sweeper, 4/day merge cap can be permanently blocked by ghost run.
- **Complexity**: XS — GH MCP comment + label add
- **Priority**: LOW urgency (Routine not yet armed). HIGH impact when Routine arms.

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
- **Value**: Round number from `ls backend/tests/test_suite_round*.py | wc -l` + 1 prevents round mislabeling; fake_supabase check prevents duplicate helper creation
- **Priority**: LOW until agent graph runtime is armed and Round N iteration resumes

## Closed / Obsolete

### Step 9G (original) — OBSOLETE as of 2026-07-28 (confirmed run 101 AM)
- **Was**: `gh workflow run kb-autopopulate.yml` when KB stale > 7 days
- **Why closed**: CCR Routine ("KB Auto-Populate (CCR)") deployed 2026-07-23 handles KB autopopulate via cloud Routine without GH Actions secrets. GH Actions broken repo-wide (#500). Implementing original Step 9G produces incorrect diagnostic.
- **Status**: Marked obsolete in governance.json run 101 AM.

### `feature-docs-trio` SKILL.md — SHIPPED run 101 AM (2026-07-28)
### Step 9F — IMPLEMENTED (run 99)
### Widget drift topic — RETIRED permanently (runs 65-70, 6 consecutive failures)
