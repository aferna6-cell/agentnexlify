# Run 101 Debate Log — 2026-08-05

**Top 3 entering debate:** Idea 1 (Step 9G merge), Idea 2 (Step 9F validation), Idea 3 (KB notes e2e test)

---

## Idea 1 — Merge Step 9G PR

### FOR
- Governance mandate fires (0 grep hits on SKILL.md main)
- KB 23 days stale — active damage to AI chat quality
- Step 9G self-heals instead of just alerting, highest operational leverage
- Already implemented in two PRs (#625, #626)
- 4+ consecutive runs carried this forward — clearly urgent

### AGAINST
- Human already knows (morning digest 2026-08-04: top priority #1)
- Two competing PRs exist — subconscious recommending again adds zero marginal information
- Subconscious is a RECOMMENDER: "recommend but do not implement." Recommending what a human already knows about is wasted signal
- Subconscious recommending Step 9G a 5th time is noise, not insight
- Actual blocker: human decision on #625 vs #626 — subconscious can't resolve it

### VERDICT: WEAKENED
Still valid, but subconscious value-add is near-zero on this run. Belongs in governance mandate escalation section, not as the winner. Human action unblocked and pending for 13+ days. A 5th recommendation is not what breaks the logjam.

---

## Idea 2 — Validate Step 9F Firing

### FOR
- KB 23 days stale with no Step 9F output in Aug 1-5 logs — possible silent failure
- If Step 9F is broken, Step 9G (when merged) would never fire — foundational
- Silent failure class is exactly what subconscious should catch
- Small investigation, focused diagnostic

### AGAINST
- Cannot verify GH #403 comment history from repo-local evidence alone
- "Absence of Step 9F in nightly-commit-review logs" may just mean format changed (ops logs vs full SKILL output)
- Two plausible explanations, no definitive data either way
- Even if confirmed broken, fix is: edit SKILL.md bash block — a LOW complexity item the nightly review bot should catch
- Step 9G (when merged) subsumes Step 9F's function — self-repair makes staleness detection less critical

### VERDICT: WEAKENED
Investigation worthy but depends on GH #403 access. Subconscious can file it as a parking lot diagnostic. Not the winner — confidence is MEDIUM and Step 9G supersedes it anyway.

---

## Idea 3 — KB Notes End-to-End Widget Retrieval Test

### FOR
- Fresh evidence: feature 4853c31 shipped 3 days ago (2026-08-02), 8 insert-path tests, ZERO retrieval/context tests
- Exact precedent: booking CTA bug (2026-07-23) — URL shared by AI (worked), but widget renderer didn't linkify (failed). Same "works in isolation, breaks end-to-end" class
- All 3 live tenants use KB-backed AI chat; wrong KB retrieval = wrong AI responses = direct customer impact
- XS-to-S effort: one integration test file, no new prod code
- Subconscious adds unique value here — nightly commit review approved 4853c31 without flagging retrieval gap (correct, that's not its job)
- Test is concrete: insert note → search KB → assert note in results → assert note in assembled widget context

### AGAINST
- KB notes feature still <1 week old — may be too early for customers to find the gap empirically
- If the widget chat already calls a search function that naturally includes `source='note'` rows, gap may not exist
- Writing the test requires understanding the KB search path (`backend/services/knowledge_base.py` or similar)

### COUNTER
- "May not exist" is exactly what the test resolves. If no gap → test passes and confirms correctness. If gap → caught before customers find it
- 3 days old is when test coverage should be added, not later
- KB search path is well-bounded: the insert test in test_tenant_kb.py already shows the relevant service functions

### VERDICT: SURVIVES → WINNER
Highest evidence-to-action signal. Fresh feature, known failure class, clear test spec, confirmed gap in existing test coverage. Adds unique value that no other current process (nightly review, morning digest) provides.

---

## Final Rankings

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1 — Step 9G merge | WEAKENED | Governance mandate section (human already unblocked) |
| 3 — KB Notes e2e test | SURVIVES → WINNER | Winner run 101 |
| 2 — Step 9F validation | WEAKENED | Parking lot (GH #403 needed for verification) |
| 4 — client_id guard expansion | NOT DEBATED | Parking lot (carry-forward from bug-patterns.md entry) |
| 5 — Cross-phase test audit | NOT DEBATED | Parking lot (useful but discovery-only, larger scope) |
