# Debate Log — Run 33 (2026-05-24)

Top 3 ideas ranked by impact: Idea 1 (GH #181 Fix), Idea 2 (/moratorium-sprint), Idea 3 (faq_service smoke tests).

---

## Idea 1: Fix GH #181 — Add 15000+25000 to AMOUNT_TO_PLAN, fix CI-blocking tests

### Challenge 1: Third consecutive winner recommendation — if it hasn't been implemented twice, what makes this run different?

**Objection:** Runs 31 and 32 both recommended the exact same fix. The implementation sketch is already detailed in winning-concept.md from run 32. The problem isn't information — it's execution. Proposing a third time wastes the winner slot.

**Defense:** The winner slot represents the highest-leverage recommendation right now. GH #181 is still the most urgent active item: (a) billing resolution is broken for $150/$250 tenants, (b) the CI trap is an active daily hazard — any developer who adds the correct fix will see CI go red on `test_no_wrong_15000_mapping` and may revert it, believing the test is authoritative. The urgency has INCREASED since run 32. Three missed commits confirm the fix is non-obvious without this focused guidance.

**Verdict:** Objection overruled. Urgency strengthened by CI trap and third missed commit.

### Challenge 2: The CI trap is theoretical — developers would read the test's context and understand it's outdated

**Objection:** Any competent developer seeing `test_no_wrong_15000_mapping` would also read its docstring, notice the "issue #81" reference, check git blame, and conclude the test is stale. The trap isn't as dangerous as claimed.

**Defense:** The test's docstring doesn't say it's stale — it says the legacy prices (24900, 29900, 49900) are "current pricing." A developer who hasn't read CLAUDE.md and sees CI fail on their addition of `15000: "autopilot"` would see a test explicitly calling their change wrong. Docstring says legacy = current, so they revert the fix. This is a real trap, not a theoretical one. Evidence: the commit 1eaaeec by a developer titled "Fix billing AMOUNT_TO_PLAN" STILL missed 15000 and 25000 after the test file was already written. The test is actively misleading.

**Verdict:** Objection fails. Docstring "current pricing" = wrong and misleading = real trap.

### Challenge 3: Could the pre-commit sentinel (Check 11) be the winner instead — simpler, no test file edits?

**Objection:** Check 11 is purely additive (15 lines to pre-commit), no risk of changing tests incorrectly. Why not recommend Check 11 as the winner and let the billing fix follow naturally?

**Defense:** Check 11 validates that 15000 IS in AMOUNT_TO_PLAN. Since 15000 is NOT currently there, adding Check 11 immediately breaks ALL pre-commit runs. The sentinel must come AFTER the billing fix, not before. Check 11 is a bonus step, not a standalone winner.

**Verdict:** Objection fails. Check 11 is a post-fix sentinel, not a substitute for the fix.

**Idea 1 Final Verdict: SURVIVES → WINNER**

Evidence strength: HIGH (4 independent sources: direct inspection, GH #181, three failed commits, CI trap confirmed). S-effort (~15 min). Moratorium-safe. CI booby-trap adds urgency beyond runs 31+32.

---

## Idea 2: Invoke /moratorium-sprint (Items A+B+D, ~40 min)

### Challenge 1: Nine consecutive recommendations (runs 25–33). By the freeze_threshold rule, this should be approaching frozen status.

**Objection:** The freeze_threshold=3 applies to rejected_paths entries. /moratorium-sprint has been recommended 8 times (runs 25-32) without invocation. This is effectively a rejected path — the human consistently doesn't invoke it. At what point does the subconscious stop recommending things that aren't acted on?

**Defense:** The freeze_threshold applies to ideas the human explicitly REJECTS. /moratorium-sprint has never been explicitly rejected — it's pending_approval and the tool exists. The bottleneck is commitment (40 min), not rejection. The moratorium-sprint IS the standing path to moratorium exit. Removing it from recommendations entirely would eliminate the only clear moratorium exit mechanism.

**Verdict:** Defense holds the principle but loses the winner argument. The point of the winner slot is to surface the MOST actionable recommendation. An 8x-unacted-on action isn't the most actionable this run.

### Challenge 2: If commitment is the bottleneck, what new evidence does run 33 add to make invocation more likely?

**Objection:** Every run since 25 has said "the tool is ready, just invoke it." Run 33 adds no new information. GH #181 (15 min) is a better fit for the winner slot because it requires LESS commitment.

**Defense:** The 40 min commitment for /moratorium-sprint exits moratorium entirely. GH #181 is 15 min but doesn't exit moratorium. The sprint is categorically higher-leverage. But the defense doesn't address the "no new evidence" objection.

**Verdict:** WEAKENED. The /moratorium-sprint remains the standing highest-leverage action (noted in improvement-backlog.md), but loses the winner slot for the third consecutive run. Not frozen — just demoted to standing direction. The 9th identical recommendation would add no marginal value over the 8 previous.

**Idea 2 Final Verdict: WEAKENED → Standing action (not winner)**

---

## Idea 3: faq_service.py + industry_faqs.py smoke tests

### Challenge 1: industry_faqs.py may be data (static content), not logic. Coverage tests on static data provide little value.

**Objection:** Without reading industry_faqs.py, we can't confirm it has function logic worth testing. If it's a dict of strings, a "smoke test" is just verifying that a Python file imports without error — minimal ROI.

**Defense:** The file is 415 lines, extracted from a 600+ line branding_service.py god class during a major refactor. At that size, it almost certainly has function-level logic beyond raw data. The pattern from 2174732 is: extract service → write test file. Missing this one breaks the pattern.

**Verdict:** Defense is plausible but relies on inference, not evidence. The objection correctly identifies that we'd need to read the file before committing to this as a winner.

### Challenge 2: This is M-effort (30 min) vs GH #181 S-effort (15 min) during active moratorium. The moratorium protocol favors S-effort items.

**Objection:** Moratorium protocol prefers S-effort items. 30 min to write coverage tests for services that probably work fine (refactor was rated MEDIUM risk, nightly review clean) is harder to justify than the 15-min billing fix with an active CI trap.

**Defense:** 30 min is a loose estimate. But the objection stands: billing fix has a specific, provable harm (CI trap). Coverage gap for faq_service is probabilistic harm.

**Verdict:** Objection holds. GH #181 has proven harm; faq_service gap is unproven harm.

**Idea 3 Final Verdict: WEAKENED → Parking lot**
Precondition before promoting to winner: read faq_service.py + industry_faqs.py to confirm function logic content, not static data. If logic-heavy: run 34 candidate.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| GH #181 Fix | SURVIVES | WINNER |
| /moratorium-sprint | WEAKENED | Standing action |
| faq_service smoke tests | WEAKENED | Parking lot (verify content first) |
| widget_config_service smoke | Not debated | Parking lot |
| CLAUDE.md AMOUNT_TO_PLAN note | Not debated | Bonus step alongside winner |
