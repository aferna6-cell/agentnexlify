# Debate Log — Run 32 (2026-05-23-pm)

Top 3 ideas ranked by evidence strength and moratorium-safety: Idea 1 (GH #181 Billing Fix), Idea 2 (dashboard_service coverage), Idea 3 (/moratorium-sprint).

---

## Idea 1: GH #181 Billing Fix (Run 31 Continuation)

### Round 1: Initial Challenge

**Challenge:** Run 31 made this exact recommendation. Two consecutive same-winner runs mirror the moratorium repeat pattern that consumed runs 15-27. What's genuinely different now?

**Defend:** Three things changed between run 31 and run 32:

1. **1eaaeec failed the fix in public.** A commit explicitly titled "Fix billing AMOUNT_TO_PLAN" landed this morning. It removed the wrong mappings (correct) but left 15000 and 25000 absent (incorrect). This is new evidence — the fix is non-obvious enough that a developer working on it directly still missed the critical entries. The recommendation isn't just "add 2 dict entries" — it must also explain WHY those entries are the right ones (CLAUDE.md plan prices, not the legacy prices in the test docstring).

2. **CI now actively blocks the correct fix.** 1553bf7 wired test_billing_amount_to_plan.py into CI immediately after 1eaaeec. If a developer adds `15000: "autopilot"` and `25000: "professional"` tomorrow, CI will go RED on `test_no_wrong_15000_mapping` (asserts `15000 not in AMOUNT_TO_PLAN`). They'll see a failing test and likely REVERT the fix. The contradictory test is now a booby trap, not just a documentation problem.

3. **The test docstring actively misleads.** It calls 24900/29900/49900 "current pricing" — they are legacy prices from a previous Stripe price configuration. Any developer reading this file to understand billing will come away with the wrong mental model.

**Verdict after Round 1:** Evidence significantly stronger than run 31. Not a moratorium-repeat because there is new causal evidence (1eaaeec + 1553bf7). Proceed to Round 2.

---

### Round 2: Leverage Challenge

**Challenge:** Is fixing 2 dict entries + 4 test methods the highest-leverage thing to do? The god-class refactor (2174732) was a 5038-line structural change with possible uncovered services. Shouldn't coverage of dashboard_service.py take priority?

**Defend:** Billing bugs have silent downstream effects. `_resolve_plan()` is called on every Stripe webhook. A tenant paying $150/mo who lacks `metadata.plan` in their webhook resolves to `None` — leading to any default or error path that consumes that None. Silent plan misidentification. The god-class refactor risk is speculative (coverage may already exist in test_extracted_services.py); the billing gap is confirmed by direct code inspection.

Additionally, billing.py is now a frequent-change file (3 commits in 2 weeks: 821f660, c72b535, 1eaaeec). High-churn files with known gaps are highest-risk for compounding errors.

**Verdict after Round 2:** SURVIVES. Highest-leverage code_health fix with zero ambiguity about scope.

---

### Round 3: Moratorium-Safety Challenge

**Challenge:** The moratorium is active. Does a billing code fix require moratorium approval? Or is it moratorium-exempt like the sprint items?

**Defend:** Per moratorium protocol (established run 8 onwards), moratorium restricts recommending NEW features and NEW customer-facing changes. Code fixes and test corrections that address confirmed bugs are moratorium-safe — they don't add to pending_approval count in the moratorium sense; they close an open GH issue. GH #181 is filed. This recommendation closes it. The sprint items (A/B/D) are also in the pending queue but they require their own separate approval mechanism (draft PR + human review).

GH #181 is a bug, not a feature. Moratorium-safe by definition.

**Final Verdict: SURVIVES → WINNER**

---

## Idea 2: dashboard_service.py + conversations_service.py Coverage

### Round 1: Evidence Challenge

**Challenge:** We don't actually know that dashboard_service.py and conversations_service.py are uncovered. test_extracted_services.py is 897 lines — it could easily cover both. This recommendation is based on absence of evidence (their names don't appear in test file names), not evidence of absence (coverage gap confirmed).

**Defend:** The commit message explicitly names the 5 god classes refactored: "branding_service, control_center, channels_facebook, pipeline, social_media." dashboard_service is not in that list — it was created incidentally during the refactor (extracted from control_center or main.py). The 5 test files align with the 5 named god classes plus facebook_oauth. dashboard_service.py handling dashboard aggregation is a new concern.

**Challenge:** Still requires reading test_extracted_services.py before claiming a gap. This is speculative work being proposed as a recommendation.

**Defend:** ...true. The recommendation should be to VERIFY coverage, not assume the gap. But that makes it a research task, not an implementation recommendation.

**Verdict after Round 1: WEAKENED.** Valid concern but requires verification step before it becomes an actionable recommendation. Better framed as a question for the next run.

### Final Verdict: WEAKENED → Parking Lot. Add to "Questions for Next Run": verify dashboard_service.py and conversations_service.py coverage in test_extracted_services.py.

---

## Idea 3: Invoke /moratorium-sprint

### Round 1: Novelty Challenge

**Challenge:** This has been the top recommendation for 8+ consecutive runs. No new information. Recommending it again adds nothing — the bottleneck is not information, it's commitment.

**Defend:** The tool is ready. The items are pre-written. If the human is present in an interactive session, a reminder is still useful. Run 25 coined this: "Invoke /moratorium-sprint... If not invoked by run 26: escalate."

**Challenge:** Run 29 already noted: "7 consecutive /moratorium-sprint recs without invocation signals commitment (40 min) is the bottleneck." That was 3 runs ago. Nothing has changed. Repeating the same mechanism when evidence shows it doesn't work is the definition of doing the same thing and expecting different results.

**Defend:** What mechanism should replace it then? GH issues were tried (run 21, 29) — three times, never implemented. Governance changes were tried (run 20) — never implemented. The sprint is still the only mechanism that would directly exit the moratorium.

**Counter:** The sprint is "standing highest-priority action" per every run since run 25. It doesn't need to be the winner to be recommended. Elevating it to winner slot for the 9th time wastes the winner slot that could point to a concrete, fresh improvement.

**Final Verdict: WEAKENED → Standing action. Not winner. Appears in backlog under Active as standing directive.**

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| GH #181 Billing Fix | SURVIVES → WINNER | Run 32 recommendation |
| dashboard_service.py coverage | WEAKENED | Parking lot + question for run 33 |
| /moratorium-sprint | WEAKENED | Standing action, not winner |
| Zapier plan_status (GH #107) | Not debated (moratorium protocol) | Parking lot, first post-moratorium winner |
| Pre-commit billing sentinel | Not debated | Parking lot bonus (implement alongside GH #181) |
