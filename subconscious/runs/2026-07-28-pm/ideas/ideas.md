# Ideas — Run 102 PM (2026-07-28)

**Run:** 102 (PM run)  
**Evidence window:** 2026-07-21 → 2026-07-28  
**Generated:** 5 ideas

---

## Idea 1 — Step 9H: Silent-green tenant heartbeat in nightly SKILL.md

**Action:** Add Step 9H to `.claude/skills/nightly-commit-review/SKILL.md`: query `conversations` table for `agent_os` tenants with 0 conversations in 7 days; create GH issue if found. Dedup: skip if same `client_id` already has an open issue in last 7 days.

**Evidence:** `docs/dev-knowledge/bug-patterns.md` — "Silent-green automation: paying tenant's widget missing 5+ weeks, nobody noticed. Monitoring watched our surfaces, not per-tenant outcomes." `docs/dev-knowledge/customer-gaps.md` — Keys Koffee class silent churn documented as HIGH priority prevention pattern.

**Impact:** HIGH customer retention. Prevents silent churn on `agent_os` ($99.99/mo) tenants. Pattern that caused Keys Koffee loss would be caught within 7 days.

**Risk:** Prerequisite unmet — `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` availability in nightly CCR bash environment not verified. False positive if tenant intentionally inactive (holiday, seasonal business). Dedup design needed.

**Category:** nightly-step  
**Effort:** MEDIUM  
**Freeze candidate:** NO

---

## Idea 2 — Update `god-class-splitter` SKILL.md with backward-compat re-export + test patch-target patterns

**Action:** Add 2 paragraphs to `.claude/skills/god-class-splitter/SKILL.md`:
1. After the split: original file keeps `from .new_module import <names>` re-exports so existing imports don't break.
2. Before running tests: grep all test files for `patch("backend.routers.<old_file>.*")` and update patch targets to the new module path.

**Evidence:** `docs/skill-discovery/2026-07-27.md` §"Existing Skill Updates" — both omissions explicitly documented with HIGH priority. Both god-class splits this week (`calls.py` → `calls_webhooks.py`, `email_sequences.py` → split modules) caused IMMEDIATE test failures from exactly these 2 missing steps. Skill discovery marked this HIGH: "both omissions cause test failures immediately after the split."

**Impact:** Prevents recurring test failures immediately after every future god-class split. These are the 2 most error-prone steps: easy to forget, hard to debug without knowing to look for them. XS effort to document; MEDIUM+ effort each time it's missed.

**Risk:** Zero production risk. SKILL.md edit only. Channel proven. No code changes.

**Category:** skill-update  
**Effort:** XS  
**Freeze candidate:** NO

---

## Idea 3 — Step 9G CORRECTED: CCR Routine health monitor in nightly SKILL.md

**Action:** Add corrected Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: if KB stale >7 days AND no KB PR from CCR in 48h (`gh pr list --search "head:kb-autopopulate"`), comment on GH #403 "CCR Routine may be stalled."

**Evidence:** AM run (run 101) marked original Step 9G OBSOLETE. AM run's `improvement-backlog.md` designates corrected Step 9G as run 102 near-term carry-forward candidate. Original Step 9G would trigger `gh workflow run kb-autopopulate.yml` — wrong because CCR Routine is the active path and GH Actions broken (#500).

**Impact:** Monitoring gap: CCR creates KB PRs but nightly can't verify CCR is alive. Would catch stalled CCR Routine within 7 days. KB currently healthy (5 days since last run).

**Risk:** False positive risk — `gh pr list` search must distinguish "0 PRs in 48h" from "N PRs open unmerged." Design complexity: medium. PR #577 currently contains OBSOLETE Step 9G — merging it without this fix produces wrong diagnostic.

**Category:** nightly-step  
**Effort:** MEDIUM  
**Freeze candidate:** NO

---

## Idea 4 — GH issue comment + `ai-ready` label on #605 (autonomy sweeper bug)

**Action:** Comment on GH #605 with root cause analysis: crash mid-verify strands autonomy run in `running` state permanently, no sweeper, reproduced at cycle 7. Add `ai-ready` label to enable future autonomous execution via issue-to-pr-loop.

**Evidence:** `ops/routines/logs/morning-digest-2026-07-28.md` lists #605 as second priority after GH Actions spending limit. `ops/routines/logs/nightly-commit-review-2026-07-28.md` — awareness note on autonomous merge capability not yet armed. The sweeper is a prerequisite before arming the Routine safely.

**Impact:** Unblocks autonomous engineering loop. Without the sweeper, the graph can strand in `running` state and the 4/day merge cap can be permanently blocked by a ghost run. `ai-ready` label enables issue-to-pr-loop to pick it up and implement autonomously.

**Risk:** Low. Comment only. No code changes. GH Actions currently broken so `ai-ready` label can't trigger issue-to-pr-loop CI until #500 resolves — but label staging is correct.

**Category:** gh-triage  
**Effort:** XS  
**Freeze candidate:** NO

---

## Idea 5 — Comment on PR #577 flagging obsolete Step 9G (do not merge as-is)

**Action:** Post GH comment on PR #577 via MCP: "Step 9G in this PR triggers `gh workflow run kb-autopopulate.yml` — THIS IS OBSOLETE. The CCR Routine (cloud session, not GH Actions) now handles KB autopopulate. GH Actions are broken (#500). Merging as-is will produce incorrect diagnostic on #403. Do not merge until Step 9G is updated to use `gh pr list` CCR health check instead."

**Evidence:** AM run's `winning-concept.md` §"Step 9G Governance Note" — complete explanation of why original Step 9G produces wrong diagnostic. Morning digest said "safe to merge" but was written before AM run confirmed obsolescence. PR is 4 days old, CI red.

**Impact:** Prevents bad SKILL.md from landing. Merging PR #577 as-is would add a nightly step that calls `gh workflow run kb-autopopulate.yml` → fails silently (GH Actions broken) → never comments on #403 → monitoring gap persists, owner thinks it's working.

**Risk:** Near zero. Comment only. Does not block the PR permanently — just flags the specific issue and correct replacement approach.

**Category:** gh-triage  
**Effort:** XS  
**Freeze candidate:** NO
