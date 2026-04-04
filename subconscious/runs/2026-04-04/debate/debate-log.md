# Debate Log — 2026-04-04

## Idea 1: Fix the failing test

**Challenge:**
- Is this really the highest-leverage thing? It's one test. The other 55 pass.
- The test might be testing the OLD behavior (no signature enforcement). Fixing the test to accept the new behavior is just test maintenance, not improvement.
- This won't compound — it's a one-off fix.

**Defense:**
- A red test suite is a broken foundation. Every other improvement (new features, refactors, security patches) relies on tests being green. The CRITICAL fixes agent, dead code agent, and MEDIUM fixes agent all ran tests as verification. One red test means the verification step is unreliable.
- It's not just test maintenance — it validates that the new webhook signature enforcement actually works correctly.
- It's small (30 min) but unblocks everything else.

**Verdict: SURVIVES** — Small but foundational. Unblocks all other work.

---

## Idea 2: Apply 4 existing skill updates from weekly discovery

**Challenge:**
- Is this urgent? The stale skills have been stale for days/weeks already. Nothing is on fire.
- The migration number in feature-build is wrong ("after 032" vs actual 081) but developers can just check `ls migrations/`. The skill is a convenience, not a gate.
- Updating 4 skills at once is 4 changes bundled. If one update is wrong, you've contaminated 3 good ones.

**Defense:**
- The RLS policy verification in schema-guard is NOT a convenience — it's a safety net. The MTOptions audit (commit `f18faa5`) found 120 of 146 sessions silently failing due to missing RLS policies. This is the #1 bug class. Adding it to schema-guard prevents recurrence across ALL future schema work.
- The stale migration number will cause a collision. If someone trusts the skill and creates migration "033", it'll conflict with the existing 033.
- These are 4 independent line-level edits to 4 different files. Low risk of cross-contamination.

**Verdict: SURVIVES** — The schema-guard RLS check alone justifies this. The rest is low-risk high-value.

---

## Idea 4: Build AI-to-human handoff

**Challenge:**
- This is a FEATURE, not an improvement. The subconscious should recommend improvements to the system, not new product features. Feature decisions belong to the product roadmap.
- The implementation is non-trivial: real-time notifications, conversation state management, team routing, UI changes. This is a multi-week project, not an atomic recommendation.
- There's no evidence that current users are hitting this gap TODAY. The customer gaps doc is from simulations, not real user complaints.

**Defense:**
- Fair point on scope. This is too large for an atomic subconscious recommendation.
- The simulations are evidence, but not production evidence.

**Verdict: KILLED** — Too large for an atomic recommendation. Should go through `/new-feature` pipeline instead. The subconscious should flag it as a reminder, not try to build it.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| 1. Fix failing test | SURVIVES | Foundational — unblocks all verification |
| 2. Update 4 stale skills | SURVIVES | RLS check prevents #1 bug class recurrence |
| 4. AI-to-human handoff | KILLED | Too large for atomic recommendation; belongs in feature pipeline |
