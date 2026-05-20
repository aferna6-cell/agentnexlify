# Debate Log — Run 26 (2026-05-20)

Top 3 ideas (by immediate leverage given moratorium state), debated 3 rounds each.

---

## Idea 1: Invoke /moratorium-sprint — 3 Items Remain After Item C Completed Today

### Round 1

**Challenge A:** This is the same recommendation as run 25. Run 25 was not implemented. Runs 22–25 all pushed for moratorium-exit actions and none were executed. Why would run 26 be different?

**Defend A:** Two things are different. First, the sprint load is lighter: Item C (Moratorium Escalation Protocol) was autonomously completed today by the nightly review (2ce31b2). Sprint is now A + B + D = ~40 min, not 50. Second, run 25's governance.json explicitly set a conditional: "If not invoked by run 26: escalate to nightly-commit-review as automatic trigger." This run is that boundary condition. The escalation path is now explicitly pre-written in the moratorium-sprint SKILL.md (added today by 2ce31b2 step 9A). The consequence of not invoking is now an automated trigger, not just another moratorium recommendation.

### Round 2

**Challenge B:** The nightly review implemented Item C without being told to. If we just wait, Items A and B may also be autonomously implemented in the next 1-2 nightly runs. Why burn human action when the autonomous system is working?

**Defend B:** Items A and B were NOT implemented today despite being equally LOW-risk. The nightly review implemented Item C specifically because it noticed "nightly-commit-review SKILL.md has no Moratorium Escalation Protocol section" and the nightly review is authorized to edit skill files (LOW-risk). Items A (pre-commit modification) and B (new bash script + pre-push hook modification) are higher risk in nightly-review scope — modifying hook behavior could break CI for all future commits. The nightly review correctly did NOT touch them. Item D (GitHub Actions workflow) requires `mcp__github__push_files` which the nightly review may not attempt. The sprint requires human judgment for A, B, D — the nightly review handles C, D-adjuncts, but not core hook modifications.

### Round 3

**Challenge C:** The moratorium has persisted 15 days. Every recommendation that adds "now it's really the right time" has been wrong. What makes this run structurally different from runs 22–25?

**Defend C:** Two new structural facts: (1) Item C is done — the sprint is objectively lighter and has fewer moving parts. (2) The escalation path is now encoded in SKILL.md — if the human doesn't invoke /moratorium-sprint, the nightly review will create a GH issue with escalation commentary within 24 hours. The recommendation is now backed by an automated failsafe. The sprint itself is 3 known-good items with pre-written sketches, zero dependency conflicts, and a skill that exists and has been validated.

**Verdict: SURVIVES → WINNER.** Same recommendation as run 25 but with new evidence (Item C done, sprint lighter, escalation encoded). No new mechanism needed — the existing mechanism is correct and the situation has improved.

---

## Idea 2: Authorize Nightly Review to Autonomously Execute Items A + B

### Round 1

**Challenge A:** The nightly review has LOW-risk autonomous scope by design. Adding explicit authorization for pre-commit hook modifications changes the risk profile. A broken pre-commit hook blocks all future commits repo-wide — it's not the same class of risk as adding a section to a skill file.

**Defend A:** Items A and B have pre-written implementation sketches with exact code. The risk of getting them wrong is low. The nightly review is already running `python3 scripts/check_project_invariants.py` implicitly as part of verification steps — it knows the script.

### Round 2

**Challenge B:** The nightly review autonomously implemented Item C today because it was within the natural scope of the review (skill file addition). Items A and B are outside that natural scope — they require actively reaching into the governance.json backlog and matching items to implementation sketches. This is the moratorium-sprint skill's job, not the nightly review's.

**Defend B:** Idea 2 proposes explicitly updating the nightly review SKILL.md to scope these actions. It's an authorization change, not an inference requirement.

### Round 3

**Challenge C:** This idea proposes expanding nightly autonomous scope specifically to work around human inaction. But the correct fix to human inaction is /moratorium-sprint (which exists, has the right scope, and is triggered interactively). Expanding nightly scope creates a parallel execution track that conflicts with the sprint PR model — if nightly does A+B and human does the sprint (A+B+D), there will be merge conflicts or duplicate commits. The two systems need to be coordinated, not parallel.

**Verdict: KILLED.** The concern in Round 2 + 3 is decisive — parallel execution tracks between nightly and sprint PR model are dangerous (merge conflicts, double commits). The correct mechanism for Items A+B is /moratorium-sprint in an interactive session. Nightly review's organic behavior (Item C) was within its natural scope; extending that scope to hook modifications would require guardrails that don't exist yet. Add to rejected_paths with reason "parallel execution conflict with sprint PR model."

---

## Idea 3: Create pre-commit-guard-add Skill

### Round 1

**Challenge A:** Moratorium protocol says the win slot belongs to whatever exits the moratorium. Creating a new workflow skill does not reduce pending_approvals. It's a productivity improvement but does not address the bottleneck.

**Defend A:** The moratorium hasn't exited despite 11 moratorium-mode recommendations. Perhaps changing the meta-level — making the next bug guard faster to add — has higher long-term ROI than the 12th moratorium-exit recommendation.

### Round 2

**Challenge B:** The moratorium-sprint SKILL.md was created as run 24's winner and that was the right mechanism change. There is already an execution-layer tool for the backlog. A pre-commit-guard-add skill would help after the moratorium exits — not during it.

**Defend B:** The nightly review could use this skill to autonomously implement Item A (Check 10) without needing the full /moratorium-sprint. That's a genuine path to moratorium exit.

### Round 3

**Challenge C:** The nightly review implementing Item A would still require the sprint PR for B and D. The moratorium exit path needs all 3 items in a single PR for the "one approval → pending 9→6" benefit. Fragmenting items across skill invocations loses the bundling advantage. Better: moratorium exits first via /moratorium-sprint, then pre-commit-guard-add skill ships as a standalone improvement.

**Verdict: WEAKENED → Parking Lot.** Skill discovery validated this. Not a moratorium-exiting action. Promote to run 27 first candidate when moratorium exits or when /moratorium-sprint has been invoked. Expected implementation: nightly review or next interactive session after sprint.

---

## Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| Invoke /moratorium-sprint (3 items) | **SURVIVES → WINNER** | Item C done, sprint lighter, escalation encoded |
| Authorize nightly for Items A+B | **KILLED** | Parallel execution conflict with sprint PR model |
| pre-commit-guard-add skill | **WEAKENED → Parking Lot** | Valid, skill-discovery validated, promote post-moratorium |
| Merge 4 safe dep PRs | Not in top 3 | Bonus action, remains valid independently |
| Wire check_project_invariants standalone | Not in top 3 | Item A of sprint — execute via /moratorium-sprint, not standalone |
