### Idea 4: Fix Step 9J to Check All Dependabot PRs (Not Just 2)

**Evidence:**
nightly-2026-09-05 Step 9J: "19 open Dependabot PRs total. Checked: #722, #721. Both mergeable_state:
unknown. Remaining 17 not checked this run (token budget)." At this rate, 17 PRs receive no rebase
trigger each nightly. With 48h dedup guard, each PR that was skipped waits until tomorrow. With 19 PRs
and 2 checked per run, full coverage takes 10 nightly runs (10 days). Meanwhile CVE window remains open.
The current cap of 5 rebases/run is appropriate (prevents spam), but the "not checked" skip is not
necessary for PRs in `mergeable_state: clean` — those merge immediately with no rebase needed.

**Action:**
Edit Step 9J in SKILL.md:
- Change PR checking loop to iterate ALL open Dependabot PRs (not first N).
- For `mergeable_state: clean` + no blockers → merge immediately (no cap needed, no token cost).
- Cap of 5 applies only to `@dependabot rebase` triggers (stateful GitHub comments).
- Log updated: "Step 9J: {total} checked, {merged} merged, {rebase_triggered} rebase-triggered,
  {skipped_dedup} dedup-skipped."

**Impact:**
All 19 Dependabot PRs reviewed each nightly. Any mergeable PR merges same day CI passes.
Security patches move from 10-day lag to 24h.
Category: operational / workflow
Effort: S (SKILL.md loop boundary change)
