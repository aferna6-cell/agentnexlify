# Debate Log — Run 128 (2026-09-24)

## Context
Run 127 winner (Step 9E P0 tier, 7th carry) was IMPLEMENTED by nightly-2026-09-24 via autonomous-executable channel. Run 128 is free to pick a fresh direction. Top 3 ideas debated below.

---

## Idea 1: Step 9J Priority Queue (sort:created-asc + perPage=5)

**Proposition:** Change Step 9J.1 search query to add `sort:created-asc` and cap `perPage=5`. This ensures the 5 oldest Dependabot PRs are always processed first within token budget.

**For:**
- Evidence is direct and repeating: 7+ consecutive nightly runs show 17/19 Dependabot PRs skipped. Token budget depletes before Step 9J processes all results from the current unsorted list.
- Oldest PRs carry highest CVE-age risk. Current behavior may process newer PRs first (insertion order from search) while leaving week-old CVE PRs perpetually skipped.
- Fix is XS: 1-line SKILL.md edit changing the search call parameters. Same category as Steps 9F/9G/9I/9J/9K/9L — all SKILL.md edits, all implemented via autonomous channel.
- No blast radius: Step 9J only processes PRs that already pass CI + are Dependabot-authored. The sort/limit change affects which PRs get attention, not HOW they're processed.
- Autonomous-executable: YES. Same channel that implemented Step 9G (run 127). First carry.

**Against:**
- We don't have direct evidence that oldest PRs are actually being skipped vs processed. The "17/19 skipped" evidence is from nightly logs but doesn't specify which PRs.
- perPage=5 hard cap means if one PR blocks (merge conflict, CI failure), we might process only 4 viable PRs. Current behavior at least surfaces all 19 for token-budget consideration.
- The underlying problem (token budget depletion) isn't fixed, just its symptom. A deeper fix would be Step 9J budget reservation or a separate dedicated Dependabot run.

**Debate verdict:** SURVIVES → **WINNER**

The "against" points are real but minor. The symptom fix (oldest-first) is the right immediate action: until token budget is properly managed, ensuring the highest-CVE-age PRs are always processed is strictly better than random/insertion-order processing. The perPage=5 counter-argument misreads the design — 5 is a per-run cap, not a hard filter on viable PRs. Next run processes the next 5 oldest. Counter to deeper-fix critique: SKILL.md is the right layer for this change; a task-budget fix would require backend service changes outside the nightly reviewer's scope.

---

## Idea 2: GH #881 Spec Enhancement Comment

**Proposition:** Read GH #881 body; if split spec for os_tool_executions.py is incomplete (missing module names, public API contracts, migration path), post an enhancing comment that unblocks issue-to-pr-loop when AUTOPILOT_GH_TOKEN rotates.

**For:**
- os_tool_executions.py at 783 lines has been in the subconscious for 7 consecutive runs. GH #881 is filed but issue-to-pr-loop can't execute until AUTOPILOT_GH_TOKEN rotates.
- Pre-populating the spec now means the loop executes the split correctly on first attempt post-rotation, without another spec-clarification cycle eating a run.
- One-off comment action with no SKILL.md edits required.

**Against:**
- AUTOPILOT_GH_TOKEN expires 2026-10-02 — 8 days from today. If not rotated, the comment is wasted effort; if rotated, the loop will likely read #881 and generate its own implementation plan.
- The spec quality question is secondary to whether the token rotates. Spending subconscious attention on improving a spec for a blocked loop optimizes for a condition that may not occur within 8 days.
- No persistent improvement: a comment on GH #881 doesn't update SKILL.md, governance.json, or any durable state. The subconscious cycle's value is maximized by changes that outlast the current run.

**Debate verdict:** WEAKENED → Parking lot

Valid concern about the token expiry horizon. The comment is worth doing but not as the run 128 winner — it belongs in the nightly review's "actions" phase (Step 9L-adjacent), not as the subconscious improvement vector. Parking: nightly can post it as a low-cost action if GH #399 sees movement.

---

## Idea 3: Credential Liveness Test (Step 9O)

**Proposition:** Add Step 9O to nightly SKILL.md making a test API call to verify AUTOPILOT_GH_TOKEN is not early-revoked.

**For:**
- Catches unexpected revocation before automation goes dark.
- XS effort — one SKILL.md addition.
- Complements Step 9E's schedule-based detection with a liveness check.

**Against:**
- Step 9E P0 tier was just implemented by nightly-2026-09-24 (run 127 winner). It fires daily escalations with 8 days remaining. The P0 signal is already present and strong.
- No evidence of early revocation risk. GH #893 was closed "not_planned" — the owner is aware but not treating it as urgent. Adding liveness detection solves a hypothetical failure mode with no historical precedent in this codebase.
- Each additional Step 9N+ added to nightly SKILL.md consumes token budget. The core problem (token budget depletion causing 17/19 Dependabot skips in Step 9J) is actively degrading security posture. Adding another step worsens budget pressure.
- "Brain connector also failed on the same date as the last expiry event" evidence cited in Idea 3 is speculative — single data point, no causal link confirmed.

**Debate verdict:** KILLED

Step 9E P0 is the right layer for credential urgency — it's schedule-based and fires daily. Liveness detection adds complexity without proportionate risk reduction. Token budget pressure argues against adding steps. Revisit if: (1) Step 9E fires EXPIRED state (days_remaining <= 0) and token still hasn't rotated, indicating the escalation chain failed, OR (2) there's a documented case of early revocation in the credential rotation log.

---

## Synthesis

**Winner: Idea 1 — Step 9J Priority Queue (sort:created-asc + perPage=5)**

Single most impactful, evidence-backed, autonomous-executable improvement available for run 128. Directly addresses the longest-running operational gap (17/19 Dependabot PRs perpetually skipped) with the smallest possible change. Ensures CVE-age risk from oldest PRs is addressed within existing token budget constraints.
