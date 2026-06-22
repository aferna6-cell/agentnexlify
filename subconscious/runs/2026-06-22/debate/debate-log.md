# Debate Log — Run 65 (2026-06-22)

Top 3 ideas ranked by impact: Idea 1 (plan-name guard, S-effort, autonomous), Idea 2 (AI-to-Human Handoff, customer #1 gap), Idea 3 (widget_chat.py split, code health).

---

## Idea 1: Plan-name Guard Check 7 to check_project_invariants.py

### Challenge

**C1: Is the evidence strong enough?**
The repricing gap was 6 days, but `test_plan_gating_new_plans.py` now LOCKS the constants with 90 assertions. If a future coder omits a plan, the test suite catches it before merge. Why add another guard?

**C2: Is this the highest-leverage thing to do right now?**
AI-to-Human Handoff has been Critical for 57 days. check_project_invariants Check 7 is Bonus B from run 64 — explicitly framed as a follow-on, not a primary recommendation. Does it deserve the winner slot over a 57-day customer gap?

**C3: What could go wrong?**
The check reads private variables (`_UNLIMITED_PLANS`, `_ALLOWED_PLANS`) from service modules. If the variable name changes as part of a refactor, the check would start failing on EVERY commit — false alarm fatigue.

**C4: Has something similar been rejected?**
No. This specific check was explicitly recommended as Bonus B in run 64 and the pre-condition (GH #292/#293 fixed) was set. It has never been debated independently.

**C5: Is this too similar to the active direction?**
The active direction (GH #292/#293) is now IMPLEMENTED. This is the explicit follow-on — not a duplicate.

### Defend

**D1:** test_plan_gating_new_plans.py catches the bug at PR time IF the test is run. But tests can be skipped in a fast fix (`--no-verify`), and the gap with GH #292/#293 was partly because no gate existed at the commit layer. check_project_invariants is wired into pre-commit (Check 13 per `bc91e97`) — it runs on EVERY commit, not just in CI. Defense-in-depth: both layers needed.

**D2:** AI-to-Human Handoff is M-effort (~1 day) with product decisions (trigger strings, schema migration, owner notification UX). Plan-name guard is S-effort (~15 lines Python, ~30 min). These aren't competing in the same execution queue. Doing the guard today doesn't delay AI-to-Human Handoff. Governance discipline: take the S-effort win first, then schedule the M-effort.

**D3:** Variable name stability is valid. Mitigate: the check reads the constant directly from the module (same as test_plan_gating_new_plans.py does). If the variable name changes, both the test file and the invariant check break simultaneously — the author would see two failures at once, not a phantom failure. This is a feature, not a bug: it enforces naming stability in these security-sensitive constants.

**Verdict: SURVIVES.** Highest-leverage atomic action this run. Pre-condition met. Autonomous-executable. Competes on zero criteria with AI-to-Human Handoff.

---

## Idea 2: AI-to-Human Handoff v1

### Challenge

**C1: Is the evidence strong enough?**
This idea has been recommended 7+ times since run 4 (runs 4, 21, 29, 38). It has never been implemented. The evidence strength is high; the implementation friction is clearly the bottleneck. What's different this run?

**C2: Is this the highest-leverage thing to do right now?**
The codebase just went through a major bug-fix sprint (repricing issues). The test suite is 2163 tests, 0 failed. Is now the right time for a M-effort customer feature, or does the system need consolidation first?

**C3: What could go wrong?**
Trigger string detection in widget_chat.py must be robust. False positives (widget says "talk to someone" in FAQ text) would trigger unnecessary handoffs. Schema migration for handoff_requests (Rule 8: no half migrations). Owner notification requires owner_phone/owner_email populated in tenant profile — not guaranteed.

**C4: Has something similar been rejected?**
The AI-to-Human Handoff full implementation was rejected in run 1 (too large, not atomic). Run 4 narrowed it to explicit-trigger-only v1 (atomic). That version has never been rejected — only deferred. 

**C5: Is this too similar to the current active direction?**
No active direction after the moratorium_override items resolved.

### Defend

**D1:** What's different: AI-to-Human Handoff is now the #1 open gap with ALL blocking items cleared (os_outbound_mirror ready, infrastructure solid). But the bottleneck has consistently been M-effort activation energy — not information clarity. This run does NOT have a mandate, so the winning concept must be the highest-impact ACTION. AI-to-Human Handoff requires a fresh interactive session with product decisions; recommending it as the winner without that session is unlikely to produce a different outcome than runs 4, 21, 29, 38.

**D2:** The system should consolidate with the S-effort guard FIRST (Idea 1). The guard is the lesson from the repricing gap — hardcode the protection NOW while the memory is fresh.

**Verdict: WEAKENED → Parking Lot.** Survives as the next-in-queue recommendation after Idea 1. The 7-recommendation history without implementation is not new evidence of blocking; it's evidence that scheduling friction (M-effort, product decisions needed) is the true bottleneck. This run's winner should remove that friction by putting AI-to-Human Handoff higher in next run's priority queue — but Idea 1 is the actual winner.

---

## Idea 3: Split widget_chat.py god class (1307L)

### Challenge

**C1: Is the evidence strong enough?**
widget_chat.py at 1307L was discovered this run — it's not in any prior active_directions. No active bugs are attributable to it today. The file works. CLAUDE.md Rule 9 triggers at 600L, but so does email_sequences.py (1143L) which has been pending since run 35 and has a more established case.

**C2: Is this the highest-leverage thing to do right now?**
The split requires 2-4 hours of human execution + post-split-test-repair. AI-to-Human Handoff (Idea 2) would ALSO touch widget_chat.py — and a split beforehand would make that feature easier to implement correctly. Is this enablement or premature?

**C3: What could go wrong?**
widget_chat.py is the critical path for all widget sessions. A split that breaks imports could take ALL widget sessions down. This is the highest-blast-radius file in the codebase. post-split-test-repair SKILL.md exists, but the widget code has cross-origin embed constraints that make integration testing harder.

**C4: Has something similar been rejected?**
email_sequences.py split (run 35, 41) — same class, pending 2+ months. No rejection; only scheduling deferral. widget_chat.py is a first-time recommendation.

**C5: Is this too similar to the current active direction?**
email_sequences.py split (run 41) is in active_directions as pending_approval. Two concurrent god-class splits in the same queue would be unusual — only one is practical per week given the M-effort.

### Defend

**D3:** Valid concern. widget_chat.py is the most dangerous file to split. widget_helpers.py split (run 5, `6cf4646`) took 1,673 LOC and required zero post-split issues — but that was a helpers file with clear module boundaries. widget_chat.py is a router file with request context, dependencies, and shared state. The risk profile is higher.

**D1 (re-challenge):** The evidence is precisely that CLAUDE.md Rule 9 (>600L → factor first) is being violated at 1307L with new features being added. AI-to-Human Handoff (Idea 2) would be added to this file — doing it in a 1307L router is asking for spec-drift bugs (CLAUDE.md bug-patterns.md cites two of these). Split BEFORE feature = correct sequence.

**Verdict: WEAKENED → Parking Lot.** Split is correct but timing is wrong for the winner slot. email_sequences.py split (run 41) should resolve first (precedence in active_directions). widget_chat.py split is next in the god-class queue — promote to run 66 candidate. The timing argument (split before AI-to-Human Handoff) is valid but requires human scheduling coordination that the subconscious cannot force.

---

## Synthesis

| Idea | Verdict | Notes |
|------|---------|-------|
| Idea 1: Plan-name Guard Check 7 | **SURVIVES → WINNER** | S-effort, autonomous, pre-condition met, highest leverage per unit time |
| Idea 2: AI-to-Human Handoff v1 | WEAKENED → Parking Lot | Promoted to top of next customer_value queue; scheduling friction acknowledged |
| Idea 3: widget_chat.py split | WEAKENED → Parking Lot | Correct but sequenced after email_sequences.py; promote run 66 |
| Idea 4: Fix kb-autopopulate.sh | Not debated → Parking Lot | Valid ROI 1.8, promote to next operational run |
| Idea 5: GH #263 triage | Not debated → Parking Lot | Valid investigation, promote when KB staleness causes visible harm |
