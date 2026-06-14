# Debate Log — Run 34 (2026-05-26)

## Top 3 Ideas Selected for Debate

1. Fix GH #181 — AMOUNT_TO_PLAN + contradictory CI tests (governance mandate)
2. Invoke /moratorium-sprint (Items A+B+D)
3. Split email_sequences.py (1255L) using god-class-splitter

---

## Idea 1: Fix GH #181 — AMOUNT_TO_PLAN + contradictory tests

### Round 1

**CHALLENGE:**
This has been recommended three consecutive runs (31, 32, 33) without implementation. If the fix is S-effort (~15 min), why hasn't it happened? Repeating the same recommendation a fourth time changes nothing about the bottleneck. Governance mandates are a paper tiger if they've already fired 4 times on /moratorium-sprint without result.

**DEFEND:**
The governance mandate mechanism for GH #181 is categorically different from the moratorium-sprint situation. /moratorium-sprint requires 40+ minutes of multi-step execution — activation energy is high. GH #181 is a 4-change edit: 2 dict entries in billing.py, 2 test method deletions, 2 new test methods, 1 test method update. Total code delta: ~15 lines. A developer who opens billing.py for 5 minutes can close this. The moratorium-sprint stalled because commitment was the bottleneck. GH #181 stalls because no developer has been directed to it by name with precise file locations. This run provides that.

Moreover, the governance mandate exists exactly for this: when the normal recommendation cycle fails to produce action, escalate the signal intensity. Three runs is the threshold — this is the escalation run.

**ROUND 1 VERDICT:** Idea holds.

---

### Round 2

**CHALLENGE:**
The contradictory test update is the risky part. Removing `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping` eliminates safety guards. What if 15000 and 25000 WERE incorrectly in the dict at some past point and these tests were added to prevent regression? You could re-introduce the original bug.

**DEFEND:**
This is addressed by the context. The current CLAUDE.md plan prices section states:
- `autopilot` = $150/mo
- `professional` = $250/mo

Current prices 15000 (=$150) and 25000 (=$250) are the CORRECT current mappings per plan pricing. Issue #81 was filed when these were WRONG mappings (mapping to wrong plans). The issue is now closed, but the tests remain. The new tests being added (`test_current_autopilot_pricing_150`, `test_current_professional_pricing_250`) assert the positive case — the correct current state — which is better coverage than the negative assertion. There is no regression risk: the new tests will fail immediately if wrong mappings are introduced.

**ROUND 2 VERDICT:** Idea holds.

---

### Round 3

**CHALLENGE:**
billing.py is 906 lines — approaching god-class threshold (Rule 9: 600+ lines). Fixing 2 dict entries without splitting the file is treating a symptom while the root cause (god-class billing router) remains. Is this the right level of intervention?

**DEFEND:**
No. God-class refactoring and bug fixes are independent operations. CLAUDE.md Rule 9 says "don't extend god classes — factor them out." The 2 missing dict entries are a production bug — a Stripe webhook for an autopilot subscriber paying $150/mo silently fails to resolve their plan. That's revenue-impacting. Deferring a 15-minute bug fix because the file is large violates the priority hierarchy. The billing.py split belongs in `plans/god-class-refactor_plan.md` as a separate task. Fix the bug first; split the file in a separate session with /god-class-splitter.

**ROUND 3 VERDICT:** Idea holds.

**FINAL VERDICT: SURVIVES → WINNER (governance mandate fires, 4-consecutive-run threshold)**

---

## Idea 2: Invoke /moratorium-sprint

### Round 1

**CHALLENGE:**
This has been the recommended winner in 8+ consecutive runs without invocation. Run 27 was the "FINAL interactive recommendation" and it still didn't happen. Run 28 issued a "hard mandate" — nightly review formally declined on governance grounds. What new forcing function exists in run 34 that didn't exist in runs 25-33?

**DEFEND:**
A human is present in an interactive session right now. That's the highest-probability implementation window. After GH #181 is fixed (this session's winner), the human is already in implementation mode for approximately 15 minutes. The sprint is 3 additional items totaling ~40 min. The activation energy for starting the sprint is lower when you're already in an implementation mindset.

**ROUND 1 VERDICT:** Partially valid, but not sufficient to make this the winner over a governance-mandated item.

---

### Round 2

**CHALLENGE:**
If the human is present and in implementation mode, GH #181 takes governance-mandated priority. /moratorium-sprint as winner would displace a higher-priority mandated action. Recommending it as winner a 9th time with no new information violates the spirit of the debate.

**DEFEND:**
Agreed. /moratorium-sprint remains the highest-leverage sprint action post-GH-#181. It should be a strong bonus action recommendation, not the winner. After the human completes GH #181 (~15 min), the /moratorium-sprint bonus is only 40 min incremental.

**ROUND 2 VERDICT:** Concession. Not appropriate as winner this run.

**FINAL VERDICT: WEAKENED → parking lot / standing action. Bonus after GH #181.**

---

## Idea 3: Split email_sequences.py (1255L)

### Round 1

**CHALLENGE:**
god-class-splitter SKILL.md was created 12 hours ago. It hasn't been used in practice yet. Using it on a 1255-line production file as its first real test is high-risk. If the skill has gaps (missing edge cases, wrong grep patterns), the first execution could leave stale importers or break tests. Moratorium is also still active — large refactors belong post-moratorium.

**DEFEND:**
The skill was authored from the exact pattern used in local_seo split and PR #180. Both are tested examples. The checklist is precise (Steps 6 and 10 are specifically about catching stale importers). The risk of a first execution is that it takes longer than estimated or requires iteration — not that it breaks production, since all changes are local until committed.

**ROUND 1 VERDICT:** Risk acknowledged but not fatal.

---

### Round 2

**CHALLENGE:**
The moratorium is day 21+. Running a god-class split is M-effort work that adds to the pending backlog while the moratorium exit path (sprint + GH #181) is sitting at S-effort. This is the wrong sequencing. Clear the moratorium first, then tackle M-effort refactors.

**DEFEND:**
Correct. This is the right analysis. email_sequences.py split is the right thing to do post-moratorium, not during.

**ROUND 2 VERDICT:** Concession. Wrong timing.

**FINAL VERDICT: WEAKENED → parking lot. First god-class-splitter production use, promote to winner post-moratorium after GH #181 closes.**

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Fix GH #181 (governance mandate) | SURVIVES | **WINNER** |
| /moratorium-sprint | WEAKENED | Parking lot / strong bonus action |
| Split email_sequences.py | WEAKENED | Parking lot — post-moratorium |
| AI-to-Human Handoff GH issue | Not debated | Parking lot (3x recs without action) |
| Zapier plan_status enforcement | Not debated | Parking lot (security, post-moratorium) |
