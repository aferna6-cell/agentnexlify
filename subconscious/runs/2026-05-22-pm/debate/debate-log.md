# Debate Log — Run 2026-05-22-pm (Run 30)

Top 3 by impact: Idea 1 (Billing Constants Contract Tests), Idea 3 (Test Patch Path Standard),
Idea 5 (AI-to-Human Handoff GH Issue).

---

## Idea 1: Billing Constants Contract Tests

### Challenge Round 1
**Objection:** Is this over-engineering? AMOUNT_TO_PLAN is a simple dict. One wrong commit was
fixed in one commit. That's not a recurring pattern — it's a one-time mistake.

**Defense:** The bug was live in production. An incorrect AMOUNT_TO_PLAN mapping means every
Stripe billing webhook that calls into it misidentifies the plan — subscription renewals,
downgrades, upgrades. The financial accuracy of the platform depends on this dict being correct.
One test file, S-effort. The asymmetry is extreme: 20 min to write vs potentially wrong billing
for all tenants until the next human review.

### Challenge Round 2
**Objection:** billing.py is 906 lines and explicitly HARD-STOP in the god-class plan. Any
test file that covers billing constants could inadvertently encourage slipping in billing logic
tests that then delay the proper grill-me refactor.

**Defense:** `test_billing_constants.py` tests only the constants — `AMOUNT_TO_PLAN`,
`PLAN_TO_STRIPE_PRICE`, plan name completeness. No routing logic, no Stripe SDK calls, no
fixture setup. The test file is intentionally narrow. Billing logic tests belong in a future
post-refactor test file. The scope is enforceable via a one-sentence docstring.

### Challenge Round 3
**Objection:** Prices change. If growth plan shifts to $149 next quarter, the test fails and
needs updating. Hardcoded assertions for dollar amounts are maintenance debt.

**Defense:** That's the point. When prices change, the test should fail — loudly, with a diff
showing the old and new values. The current failure mode is silent (wrong mapping, no alert,
wrong plan assigned). Explicit test failure on price change is strictly better than silent
production misconfiguration.

**Verdict: SURVIVES** — 3 rounds of challenge. Evidence strong (live production bug). Scope
narrow enough to be safe alongside HARD-STOP refactor. Maintenance cost is a feature.

---

## Idea 3: Test Patch Path Standard (Prevent Stale Mock Churn)

### Challenge Round 1
**Objection:** One 908-line repointing event (5f2cd2b) doesn't prove a pattern. Maybe
local_seo_handlers had unusually deep test coupling. Other splits might not need repointing.

**Defense:** The god-class-refactor_plan.md has 54 remaining targets. Even if half have
loosely-coupled tests, that's 27 repointing events. At 908 lines per event (local_seo baseline),
that's 24,500 lines of churn avoided. But more importantly: the _nature_ of the fix (repointing
`@patch('backend.services.X')` to `@patch('backend.routers.Y')`) is structural — any module
rename triggers it, regardless of test quality.

### Challenge Round 2
**Objection:** The impact is fully deferred. No split is scheduled yet (email_sequences is a
recommendation, not an approved sprint). Documenting a standard saves nothing until the next
split actually runs. Moratorium context means adding more docs items hurts the pending queue.

**Defense:** This is the key objection. The standard could save hours — but only once splits
begin. With moratorium active and 6 pending items, recommending a docs-only workflow standard
adds item #7 to the pending queue for deferred impact. The billing constants test is already
actionable (the bug just happened). The test standard is pre-work for work that hasn't started.

### Challenge Round 3
**Objection:** The testing-standards.md document already exists. Has Claude read it to confirm
the mock standard isn't already there? If it is, this recommendation is noise.

**Defense:** Valid — the test standard may already exist in .claude/rules/testing-standards.md.
The 5f2cd2b commit message doesn't reference any standard — it just fixes. This suggests the
standard is either absent or unenforced. But without reading the file, confidence is not 80%.

**Verdict: WEAKENED** — valid systemic concern, but deferred impact in a moratorium context.
Testing standard may already exist (unverified). Moratorium adds a 7th pending item without
immediate return. Demote to parking lot. Promote when first god-class split PR opens.

---

## Idea 5: AI-to-Human Handoff GH Issue

### Challenge Round 1
**Objection:** Runs 21 + 29 recommended this. Neither was implemented. What's different
today that changes the invocation probability?

**Defense:** The human is ACTIVE today — billing fix + local_seo split + OS plan merge all
landed. This is the most active production day in 17 days. A human who just split a 886-line
file and fixed a billing bug is more likely to spend 5 minutes creating a GH issue than a
human who hasn't touched production in 17 days.

### Challenge Round 2
**Objection:** Run 29 explicitly said: "If GH issue not created, consider freezing the write
GH issue mechanism." That condition has now fired. This should be evaluated for freezing, not
re-recommended for a 3rd time (as run 30 winner).

**Defense:** The formal freeze_threshold is for ideas killed in debate 3 times, not for pending
non-implementations. The mechanism isn't broken — the human simply hasn't done it. However,
run 29's instruction is a strong signal: recommending this as winner for a 3rd consecutive time
without new forcing function degrades the subconscious's credibility.

### Challenge Round 3
**Objection:** The subconscious cannot create GH issues — it only recommends. The winning
concept creates the issue spec (already written in run 29). Recommending it again is
recommending the same spec for the 3rd time with no new content. Zero information gain.

**Defense:** No defense. This objection is correct. The spec exists. The human knows it exists.
Recommending it again adds no new information and damages signal-to-noise ratio in the
subconscious output.

**Verdict: WEAKENED** — correct diagnosis (human active, 36 days, 5 min) but mechanism
exhausted (3 recs without action, spec already written, no new information). Demote to parking
lot. Do NOT propose as winner again until moratorium exits. Note in improvement-backlog
for human awareness.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: Billing Constants Contract Tests | SURVIVES → WINNER | Chosen |
| Idea 3: Test Patch Path Standard | WEAKENED | Parking lot — promote when first split PR opens |
| Idea 5: AI-to-Human Handoff GH Issue | WEAKENED | Parking lot — do not re-propose as winner |
| Idea 2: email_sequences.py Split | Not debated (M-effort, moratorium) | Parking lot |
| Idea 4: models/schemas.py Split | Not debated (prerequisite, M/L-effort) | Parking lot |
