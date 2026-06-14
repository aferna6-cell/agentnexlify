# Debate Log — 2026-05-18 (Run 23)

Top 3 ranked by impact: Idea 1 (Sprint PR), Idea 5 (Autopilot investigation), Idea 4 (Auto-approve policy).

---

## Idea 1: Consolidate All 4 S-effort Items into Single Sprint PR

### Round 1 — Challenge

**Challenge:** This is isomorphic to "do the 4 S-effort items." Framing as "one PR" doesn't
create a new forcing function. The human has known about these 4 items for 2+ weeks with
pre-written implementation sketches. Bundling them into a single PR recommendation is a
presentation change, not a mechanism change. Run 15 already said "Bonus A + B together drops
pending 4→1." Run 21's winning-concept.md had the same sprint table. Neither worked.

**Defense:** Framing is mechanism. Every previous run recommended these items as SECONDARY
(bonus items inside another winner). This is the first run where the sprint PR IS the winner —
the sole primary recommendation. Higher prominence = higher attention. More critically: each
previous recommendation framed the items as *sequential* approvals ("first do A, then B, then C").
The sprint PR framing inverts this to *parallel* — one decision tree entry instead of four.
Approval cost drops 4x. Cognitive switching cost drops from "4 separate decision points across
4 separate days" to "1 decision point today."

### Round 2 — Challenge

**Challenge:** Bundling items from different categories (code_health x2, workflow x1, operational x1)
into one PR violates git discipline. If lead-qualifier-eval.yml fails CI, the entire PR is blocked
including the trivial pre-commit change. Bisectability degrades.

**Defense:** The bundling risk is real but bounded. Two mitigations: (1) The PR contains only
additive changes — new files and 3-line additions. No existing code is modified. Rollback =
revert one commit. (2) The PR can be structured as 4 commits in a single branch — each commit
is independently reviewable and cherry-pickable. The draft PR serves as a single approval gate
without sacrificing commit-level atomicity. The benefit (1 approval vs 4) outweighs the minor
revert complexity.

### Round 3 — Challenge

**Challenge:** Run 21 was also a pivot intended to "break the meta-loop." It recommended a GH
issue creation (~15 min). Also not implemented. The meta-pattern holds: whether the winner is
"3 lines to pre-commit" or "create GH issue" or "one PR for 4 items," none have been executed.
The problem is implementation motivation, not recommendation specificity.

**Defense:** Partially conceded — implementation motivation is the root cause. But the sprint
PR framing addresses this more directly than any previous winner: it quantifies the payoff
("pending 9→5, closest to moratorium exit in 23 runs"), consolidates the decision surface
(1 vs 4), and provides a single artifact to create (the branch/PR) rather than 4 separate
implementation steps. The probability of action increases with lower decision friction. This
run also enforces the governance mandate (max_pending 3→2) regardless of winner, adding
structural pressure.

### Verdict: SURVIVES → WINNER

Survives all 3 rounds. Novel framing (one PR = one approval = maximum pending reduction in one
decision), genuine mechanism change from previous runs, best answer to "how do we actually
reduce pending the fastest." Implementation sketches all pre-exist.

---

## Idea 5: Investigate Autopilot-Issue-Loop Status + Tag ai-ready

### Round 1 — Challenge

**Challenge:** "Loop confirmed dormant" appears in runs 20, 21, 22 via memory. The confirmation
method was "zero commits last 14d" — an inference, not a direct process check. If the loop
is actually running but starved of ai-ready issues, tagging 4 GH issues could trigger 4
implementations automatically. The cost is 2 commands + 4 label clicks. Expected value could
be enormous.

**Defense (of the challenge — this is the strongest case FOR Idea 5):** The inference of
dormancy is weak. Zero commits could mean: (a) loop not running, OR (b) loop running but
no ai-ready issues to process. Scenario (b) is testable in 30 seconds. If true, the sprint
would self-execute. The investigation deserves at least parking lot status.

### Round 2 — Challenge (attacking Idea 5 as winner)

**Challenge:** The investigation has three possible outcomes: (a) loop running, ai-ready tags
work → 4 items implemented automatically; (b) loop running, tags don't work → debugging needed;
(c) loop not running → restart required with unknown effort. As a winner, "investigate X and
then do Y depending on outcome" introduces conditional branching. Subconscious winners should
be unconditional, atomic recommendations. Investigation as winner = half-winner.

**Defense:** True. The investigation is a prerequisite, not the recommendation itself.
A better framing would be: "Add ai-ready label to GH issues for runs 7, 8, 14, 19" as an
unconditional action. But if the loop is dormant, the tags do nothing — wasted effort.
The conditionality is unavoidable.

### Round 3 — Challenge

**Challenge:** Even if loop is running, the 4 S-effort items may not map cleanly to ai-ready
GH issues. Run 7 (widget sync) has no confirmed GH issue number. Run 8 (check_project_invariants)
has no confirmed GH issue (the item was added as a pre-commit addition, not an issue-tracked
feature). Run 14 (#110) and run 19 (no confirmed issue) are mixed. The loop requires existing
GH issues with ai-ready labels — creating those issues AND the loop being running are both
required. Two unknowns = too speculative as winner.

**Defense:** Partially conceded. The missing issue numbers reduce confidence. However: investigating
loop status is a 30-second check that should happen in the next session regardless. Adding to
parking lot maintains visibility without making it the primary recommendation.

### Verdict: WEAKENED → Parking Lot

Strong expected value IF loop is running AND issues exist. Too much conditionality for a confident
winner. Parking lot: investigate loop status as first step in next free-choice run (run 24 or
after moratorium exits).

---

## Idea 4: Auto-Approve Micro-Guard Policy in governance.json

### Round 1 — Challenge

**Challenge:** `auto_approve: false` was an explicit design decision. The governance system
exists specifically because auto-implementation of recommendations created unknown-state
situations. Changing the approval model requires updating SKILL.md (to act on the new field)
AND governance.json. Two inter-dependent changes to meta-tooling, not production code.

**Defense:** The policy is scoped to the lowest-risk category (hook wiring, new scripts, CI files,
SKILL.md additions). These have zero production risk. The human designed `auto_approve: false`
to prevent large changes — not 3-line pre-commit additions. The policy refinement is the right
long-term move.

### Round 2 — Challenge

**Challenge:** "auto_approve_micro_guard" as a field name doesn't exist in the SKILL.md's
execution logic. Adding the field to governance.json without updating the SKILL.md leaves
dead state. If this run adds the field, the next run still needs to update SKILL.md to act on
it. The improvement is two-phase and this run only does phase 1.

**Defense:** This is a fatal flaw. A recommendation that requires a follow-up recommendation
to become effective is not atomic. The SKILL.md update could be bundled, but then the
recommendation is no longer "add a field to governance.json" — it's "update the SKILL.md
and governance.json," which is L-effort meta-tooling while production improvements sit pending.

### Round 3 — Challenge

**Challenge:** Run 23 already applies the governance mandate (max_pending 3→2). Adding a
second governance change (auto_approve_micro_guard) in the same run increases governance
complexity and creates ambiguity about which governance changes are "mandate" vs "optional."
The mandate fires because of accrued obligation; adding optional changes alongside it muddies
the audit trail.

**Defense:** Conceded. The governance state is already complex. Run 20 mandate is binding;
adding an optional governance feature in the same run risks confusion about the obligation
boundary.

### Verdict: WEAKENED → Parking Lot

Valid long-term improvement. Fatal flaw: two-phase (field + SKILL.md) means it can't be atomic
this run. Premature given active governance mandate application. Revisit after moratorium exits
and system is in steady state.

---

## Synthesis

| Idea | Verdict | Rationale |
|------|---------|-----------|
| 1: Sprint PR | SURVIVES → **WINNER** | Novel framing (1 approval = 4 items). Pre-existing sketches. Maximum pending reduction per decision. |
| 5: Autopilot investigation | WEAKENED → Parking Lot | High expected value but conditional branching. Investigate in next free-choice run. |
| 4: Auto-approve micro-guard | WEAKENED → Parking Lot | Two-phase (governance + SKILL.md). Premature alongside governance mandate. |
| 2: check_project_invariants re-escalation | (not in top 3 debate — subsumed by Idea 1) | Included as Item 1 of Idea 1's sprint PR. |
| 3: /sprint command | (not in top 3 debate) | Parking Lot — correct long-term target after sprint PR pattern is established. |

**Governance mandate fires this run (unconditional):** max_pending_approvals 3→2 applied in
Phase 6 regardless of winner. Run 20 obligation now 2 runs overdue.
