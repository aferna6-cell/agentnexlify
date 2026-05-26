# Debate Log — Run 35 (2026-05-26-pm)

Top 3 by impact: Idea 2 (email_sequences.py split), Idea 4 (billing-constant-guard Check 11), Idea 5 (PR #182 review).

Idea 1 (GH #181 escalation) serves as governance action in Phase 6, not a winner candidate.
Idea 3 (Dependabot batch) is standing operational action, not a winner candidate.

---

## Idea 2: Invoke /god-class-splitter on email_sequences.py

### Round 1

**Challenge:** GH #181 is 5 consecutive unimplemented. Recommending a 2-hour execution task when a 15-minute billing fix is pending seems like avoiding the harder decision. Does the subconscious have the authority to pivot away from CRITICAL standing action?

**Defend:** The subconscious pivot is explicitly authorized by the 5-consecutive governance threshold. GH #181 requires human action on MEDIUM-risk billing code — the subconscious cannot implement it (SKILL.md: "DO NOT implement, only recommend"). Five identical recommendations have not produced implementation. Pivoting to a new winner is the correct governance response. The billing fix is noted as "critical standing action" in the winning-concept — pivoting doesn't abandon it.

### Round 2

**Challenge:** PR #182 (invoices.py split) is already in draft. Should we finish one god-class split before recommending another? Starting email_sequences.py while invoices.py draft is pending creates parallel work for the same developer.

**Defend:** PR #182 is an existing draft — it needs review, not new implementation work. Recommending an email_sequences.py split is a separate action that the human can sequence after reviewing PR #182. The two are in parallel, not competing. Recommending email_sequences.py now puts it on the radar for the next work session, not necessarily today.

### Round 3

**Challenge:** email_sequences.py has N+1 issues in GH #112/#113 (list_enrollments, list_sequences). Splitting a file that has known query bugs risks distributing the bug pattern across two modules, making the eventual fix harder to audit.

**Defend:** The N+1 fix is in two specific functions — list_enrollments() and list_sequences(). These map cleanly to the enrollment concern (email_enrollment.py) and CRUD concern (email_crud.py) respectively. Post-split, each function has a dedicated home. The fix becomes simpler: you're fixing list_enrollments in email_enrollment.py (350L) instead of navigating 1255L. The bug doesn't "distribute" — it concentrates in the right module.

**Verdict: SURVIVES** — three rounds of objections rebutted with evidence. Clear split axis (CRUD/enrollment/processor). Governance mandate authorizes pivot from GH #181. N+1 concern resolved (concerns are aligned, not cross-cut).

---

## Idea 4: Wire Billing-Constant-Guard as Pre-commit Check 11

### Round 1

**Challenge:** Adding a guard when the current state is already broken is out of order. GH #181 should be fixed BEFORE adding a guard for the fixed state. Otherwise Check 11 itself would fail on current HEAD (since 15000 and 25000 are absent).

**Defend:** Check 11 can be written to validate the INTENDED state (what SHOULD be present) and fail only after GH #181 is applied. The check doesn't run on current HEAD until someone commits. The order is: (1) GH #181 fix — runs tests, commits; (2) Check 11 addition — pre-commit now validates the fixed state going forward. The check is forward-looking, not retroactive. Alternatively, Check 11 can be added with a `[billing-guard-skip]` bypass until GH #181 is fixed.

### Round 2

**Challenge:** Would Check 11 have caught GH #181 in practice? The bug was introduced when entries were REMOVED from AMOUNT_TO_PLAN in c72b535. Any developer who runs pre-commit after that commit would have been blocked. But the commit log shows c72b535 wasn't blocked by any guard.

**Defend:** Correct — Check 11 didn't exist when c72b535 ran. That's the point: adding Check 11 NOW ensures the next c72b535-type commit IS blocked. 1eaaeec (the failed fix attempt) changed billing.py but didn't add 15000+25000. Check 11 running at pre-commit on that commit would have output: "FAIL: AMOUNT_TO_PLAN missing key 15000 ($150/mo autopilot) — add it or this commit will break plan resolution." That's exactly the failure-before-ship pattern.

### Round 3

**Challenge:** Compared to Idea 2 (email_sequences split), Check 11 has ~20x less long-term value. Check 11 prevents a 15-minute fix per future occurrence. The email_sequences.py split saves ~40 min/week of maintenance overhead for months. Why choose the narrower improvement?

**Defend:** Check 11 can be autonomously executed by tonight's nightly review (LOW-risk bash addition, similar to Check 9 which nightly review added autonomously in 72f8204). The email_sequences.py split requires 2 hours of human execution. If we want SOMETHING implemented tonight, Check 11 is the better candidate. The question is "which is the best improvement to recommend" vs "which will actually get executed." Check 11 wins on execution probability.

**Verdict: SURVIVES (weakened)** — strong second-round defense of "would it have caught the bug." But round 3 correctly identifies that Idea 2 has 20x higher long-term value. Check 11 wins on autonomous execution probability; Idea 2 wins on value. Demoted to Parking Lot Promoted (high priority), not winner.

---

## Idea 5: Recommend Review + Merge of PR #182

### Round 1

**Challenge:** Recommending "review a PR" is operational queue management, not a systemic improvement. The subconscious is supposed to identify improvements that compound, not flag that a PR needs review. Morning digest already does that.

**Defend:** PR #182 is the first post-skill-creation production god-class split. Evaluating it against the 12-step checklist IS systemic — it validates the new skill in production and identifies gaps for SKILL.md improvement. If PR #182 skipped Step 10 (stale importer check), that's a skill gap to document.

### Round 2

**Challenge:** The god-class-splitter skill was validated by PR #180 (5 files, 135 tests, all passing). PR #182 is a routine application of a validated pattern. The first post-skill-creation use doesn't warrant subconscious-level attention.

**Defend:** PR #180 preceded the SKILL.md. The SKILL.md didn't exist during PR #180 — that's WHY the SKILL.md was written (to codify what worked). PR #182 is the first use WITH the SKILL.md as the authority. Checking whether the actual PR followed the SKILL.md is exactly the quality gate that matters.

### Round 3

**Challenge:** Even if PR #182 has gaps, the outcome is "note the gaps." That's advisory, not a systemic improvement. The subconscious should recommend actions, not audits.

**Defend:** [No strong counter. Challenge is correct. The action is advisory, not executable improvement.]

**Verdict: KILLED** — Round 3 challenge stands. Recommending a PR audit is operational and advisory, not a systemic improvement. Morning digest already flags it. Demoted to standing action note.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 2: email_sequences.py split | SURVIVES → WINNER | Chosen |
| Idea 4: billing-constant-guard Check 11 | SURVIVES (weakened) | Parking lot promoted |
| Idea 5: PR #182 review | KILLED | Standing action note |
| Idea 1: GH #181 escalation | Governance action (Phase 6) | Critical standing action |
| Idea 3: Dependabot batch | Standing operational | Human batch action |

**Winner: Invoke /god-class-splitter on email_sequences.py**

Governance action: GH #181 moves from active_directions winner to critical_standing_action. Recommendation loop halted at 5 consecutive. Future runs require new evidence or human action (implement/reject) before re-surfacing GH #181 as a winner.
