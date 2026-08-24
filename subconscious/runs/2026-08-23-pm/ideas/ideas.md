# Subconscious Run #109 — Ideas
## Date: 2026-08-23-pm

### Evidence Summary
- Step 9J absent from nightly SKILL.md (confirmed grep — 0 matches). 1st carry-forward mandate → autonomous-executable this run per governance escalation_condition.
- 19 open Dependabot PRs (vs. 6 in run 108). Includes dangerous major version bumps: react 18→19 (#586/#591/#593), stripe v11→v15 (#598), actions/checkout 4→7 (#580). Run 108 merge heuristic doesn't guard against these — critical safety gap.
- 6 open subconscious draft PRs (oldest #606: 2026-07-28 = 26 days). PRs #626 and #674 both titled "run 109" — naming collision.
- KB: 31 days stale (last: 2026-07-23). GH #403 unresolved (secrets missing from GH Actions).
- GH #669: filed 2026-08-20, 97/97 routers missing block_demo_role — no PR after 3 days.
- GH #399: Day 41+, AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked.
- Nightly-2026-08-22 log explicitly notes Step 9J unexecuted.
- PR #674 exists (2026-08-22): "subconscious: run 109 — Step 9J" — dedup guard applies.

---

### Idea 1: Step 9J — Dependabot auto-merge with major-version safety gate (CARRY-FORWARD)
**Category:** Workflow Efficiency / Operational
**Evidence:** Run 108 mandate, carry-forward escalation, 19 open Dependabot PRs aging, 4+ weeks of morning digests flagging same PRs, 5 nightly Steps already implemented via same channel.
**Core proposal:** Add Step 9J to nightly SKILL.md. Merge CI-green Dependabot PRs with no review requests and no blocking labels. CRITICAL REFINEMENT vs run 108: add major-version bump detection — parse PR title for semver major bump (X.x → Y.x where Y > X), skip those automatically. Targets patch/minor bumps only.
**Why now:** Carry-forward mandate. Governance escalation_condition: "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)." Channel proven: Steps 9C/9E/9F/9G/9I all landed via same SKILL.md edit.
**Risk:** LOW — merge heuristic with major-version gate is conservative. Skips: non-clean CI, review requests, blocking labels, major semver bumps. Only merges patch/minor Dependabot PRs where CI is clean.

---

### Idea 2: Step 9K — Stale subconscious PR closer (MANDATE CANDIDATE)
**Category:** Operational / Code Health
**Evidence:** 6 open subconscious draft PRs (oldest: 26 days). Run 109 mandate named Step 9K as candidate if count ≥3. Count is 6. PRs accumulate because subconscious creates a new branch per run without cleaning up old ones. Naming collision (#626/#674 both "run 109") is a symptom.
**Core proposal:** Add Step 9K to nightly SKILL.md. List open PRs from HEAD branch matching `subconscious:` prefix. Close any >14 days old with 0 code commits (pure docs/state only). Add closing comment: "Stale subconscious PR closed by nightly Step 9K (>{N} days, 0 code changes)."
**Why now:** Mandate candidate, 6 PRs exceeds threshold. But sequencing: Step 9J must land first (it's the carry-forward). Step 9K is run 110 material.
**Risk:** LOW — closes only stale draft PRs with no code changes. Misfire is recoverable (PRs can be reopened).

---

### Idea 3: GH #669 middleware-level block_demo_role guard
**Category:** Security / Code Health
**Evidence:** Step 9I (run 107) found 97/97 routers missing block_demo_role. GH #669 filed 2026-08-20. No PR after 3 days. Issue-to-pr-loop can't pick it up (AUTOPILOT_GH_TOKEN expired, GH #399). Architecture: adding the guard to each router individually is M-effort (97 files). Better fix: add middleware that catches demo role before any router.
**Core proposal:** File enhanced GH issue or add architecture note proposing FastAPI middleware approach (one place, not 97). Tag as `security` + `blocked-by-#399` + `ai-ready`.
**Why now:** Security gap is real (demo tenants can mutate data). But: this is M-effort, needs human-approval session, wrong channel for subconscious autonomous action.
**Risk:** HIGH if done wrong (middleware breaks normal auth). RECOMMEND as human-approval ticket, not this run's autonomous action.

---

### Idea 4: Consolidate 6 stale subconscious PRs — close orphans, keep #674
**Category:** Operational hygiene
**Evidence:** PRs #606/#617/#626/#633/#650/#674 all open. #674 is current run 109 PR. #606 is 26 days old. Manual close of 5 orphans would clean the board.
**Core proposal:** Directly close PRs #606, #617, #626, #633, #650 via mcp__github__update_pull_request (state: closed). Keep #674 as the active run 109 PR.
**Why now:** Quick wins. Cleaner PR board. But this is operational hygiene best handled as part of Step 9K (automated), not manual one-off.
**Risk:** LOW — closing draft PRs with no code changes is trivially recoverable.

---

### Idea 5: Add semver-aware Dependabot PR labeler to nightly
**Category:** Workflow Efficiency
**Evidence:** 19 open Dependabot PRs, mix of major/minor/patch. Manual inspection needed to safely merge. A labeler would tag PRs as `dep-major`, `dep-minor`, `dep-patch` enabling Step 9J to safely auto-merge `dep-patch` only.
**Core proposal:** Add Step 9L (before 9J) to nightly: for each open Dependabot PR, parse title to detect semver bump type, apply label. Then Step 9J uses label filter instead of title regex.
**Why now:** Nice refinement but over-engineers Step 9J. Step 9J's title-regex major-version check is simpler and sufficient. Labeler adds complexity without enough gain.
**Risk:** LOW technically, but scope creep for this run.
