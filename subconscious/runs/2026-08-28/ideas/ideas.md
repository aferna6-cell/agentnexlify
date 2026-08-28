# Ideas — Run 110 (2026-08-28)

## Mandate Check (run_109_mandate)

1. **Step 9J fired**: PASS — nightly-2026-08-28 shows "Step 9J: 3 PRs checked, all `mergeable_state: unknown`, 0 merged"
2. **Count merges/skips**: 3 checked, 0 merged, 3 skipped (all `mergeable_state: unknown`)
3. **Merge failure diagnosis**: Not a merge failure — all PRs have `unknown` state. GitHub hasn't computed mergeability (stale base). Step 9J requires `"clean"` — correct, but no rebase trigger means PRs permanently stuck.
4. **GH #669**: OPEN — 95 routers missing `block_demo_role`, 8 days old, no linked PR
5. **GH #403/KB freshness**: KB NOW HEALTHY — last run 2026-08-26 (2 days ago, < 7d threshold). RESOLVED.
6. **GH #399**: Step 9E shows AUTOPILOT_GH_TOKEN ~55 days, OK (< 76d threshold). BUT autopilot loop appears stalled (3 ai-ready issues 8-21d with no PRs). Token may exist; loop stall root cause unknown.
7. **Step 9K candidate**: subconscious PR count not checked this run — defer to next mandate item.

---

## Evidence Summary

- **Step 9J broken at 0%**: 20+ Dependabot PRs all `mergeable_state: unknown`. Nightly itself recommends "Trigger rebase via @dependabot comment". Fix is adding rebase trigger when state is `unknown`.
- **KB autopopulate RESOLVED**: 4 new articles compiled 2026-08-26 (GoHighLevel AI Employee, claude managed agents pricing, TCPA compliance, etc.). Not a concern for this run.
- **Brain connector stale 36d** (GH #684): root cause = SUPABASE_ACCESS_TOKEN not set in Railway. Step 9C adds comments but no escalation signal change.
- **3 ai-ready security issues all stalled**: #643 (21d, appointment_briefs.py), #660 (13d, scoring_config.py), #669 (8d, 95 routers). Zero linked PRs. Loop behavior unclear.
- **GH #669 class-wide security gap**: middleware fix would close all 95 violations in 1 PR.
- **Managed agents audit (#677)**: 7 findings fixed this week — suggests autonomous agent code quality gaps.
- **CI cleanup (#680, #682)**: unscheduling 11 workflows — ops hygiene ongoing.

---

## Idea 1: Fix Step 9J — Add `@dependabot rebase` trigger for `mergeable_state: unknown` PRs

**Evidence:** nightly-2026-08-28 confirms Step 9J fired and got 0 merges. Root cause: GitHub returns `unknown` for stale-base PRs — only `@dependabot rebase` or manual rebase triggers recomputation. 20+ PRs stuck indefinitely. Nightly log itself recommends: "Trigger rebase via @dependabot comment or merge manually after CI passes."

**Action:** Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`: when `mergeable_state == "unknown"`, check if last comment on the PR already contains `@dependabot rebase` (added in last 48h). If not, post `@dependabot rebase` comment via `mcp__github__add_issue_comment`. Log: "Step 9J: triggered rebase on PR #{N} (state: unknown)". Re-check mergeability on next nightly (will be "clean" after Dependabot rebases + CI passes).

**Impact:** Step 9J goes from permanent 0% merge rate to actively merging security dep bumps within 24-48h. ~20 PRs unblocked. CVE window shrinks.

**Category:** workflow

---

## Idea 2: Step 9K — Stale Subconscious PR Closer (report-only mode)

**Evidence:** run_109_mandate explicitly named Step 9K as run 110 candidate "if ≥3 subconscious PRs open." governance.json shows multiple subconscious PRs listed as open in active_directions (runs 90-93 include pending_human_action items). Morning digests have flagged stale draft PRs (#575, #606, #611, #613, #625, #626) across multiple runs. Old subconscious PRs create PR list noise and make it harder for humans to find actionable items.

**Action:** Add Step 9K block to `.claude/skills/nightly-commit-review/SKILL.md`: list open PRs with `head_branch` starting with `subconscious/`. For each open draft PR: check age. If >21 days old and no commits in last 14 days, post a comment summarizing status and asking human to merge or close. Log count. Report-only mode (no auto-close).

**Impact:** Reduces PR noise for human review. Surfaces which subconscious PRs are stale. Keeps PR list actionable.

**Category:** workflow

---

## Idea 3: Add ai-ready loop stall diagnostic to Step 9D (new Step 9D+ escalation)

**Evidence:** 3 ai-ready issues — #643 (21d), #660 (13d), #669 (8d) — all stalled with no linked PRs. Step 9D already logs this but doesn't escalate. GH #399 shows AUTOPILOT_GH_TOKEN ~55d (OK < 76d threshold per Step 9E) — but the loop appears dead regardless. Root cause unknown: could be token, loop config, GH Actions stall, or rate limiting.

**Action:** Enhance Step 9D in `.claude/skills/nightly-commit-review/SKILL.md`: when oldest ai-ready issue > 14 days with no linked open PR, check if a "loop-stall" GH issue already exists (search: label:loop-stall is:open). If none exists, file one with: (a) list of stalled ai-ready issues + ages, (b) last known loop execution date, (c) Step 9D diagnostic checklist (AUTOPILOT_GH_TOKEN age, GH Actions logs URL, recent workflow runs). Label: loop-stall + human-action-required.

**Impact:** Surfaces loop stall with actionable diagnostic instead of silent repetition. One clear issue for human to investigate.

**Category:** agent_performance

---

## Idea 4: Middleware-level `block_demo_role` FastAPI guard (closes GH #669)

**Evidence:** GH #669 filed 2026-08-20 by Step 9I: 95 routers missing `block_demo_role`. 8 days stale, no linked PR. Individual per-router adds scale to 95 changes + future routers will miss it again. Middleware approach: one FastAPI middleware (or base router class) checks demo role for all POST/PUT/DELETE/PATCH. Parking lot since run 108 ("M-effort, human-approval required").

**Action:** Recommend adding `DemoRoleGuard` as FastAPI middleware or router-level dependency in `backend/main.py`. Single `Depends(block_demo_role)` on the `APIRouter` base class that all mutating routers extend. Close GH #669 as fixed by middleware PR. File GH issue describing the architectural approach (not the individual fixes).

**Impact:** Closes 95 violations in 1 PR. Prevents future violations permanently. Removes reliance on per-router manual adds.

**Category:** code_health

---

## Idea 5: Add SUPABASE_ACCESS_TOKEN onboarding checklist comment to GH #684 with exact Railway path

**Evidence:** Brain connector 36 days stale. GH #684 exists (Step 9C comment added 2026-08-28 with 36-day count). Root cause confirmed: SUPABASE_ACCESS_TOKEN not in Railway env. Steps 9C comments add count updates but the exact Railway path to set the token has never been provided as a structured checklist in the issue. Human may not know WHERE to go.

**Action:** Post one targeted comment on GH #684 with a 3-step checklist: (1) Supabase dashboard → Project Settings → Access Tokens → Copy token, (2) Railway → agentnexlify → Variables → Add SUPABASE_ACCESS_TOKEN, (3) Railway deploy. Estimate: 2 minutes. End with: "Once set, brain connector will resume on next scheduled run."

**Impact:** Transforms an open issue with a count update into an actionable 2-minute task. Could unblock brain connector in same day.

**Category:** operational
