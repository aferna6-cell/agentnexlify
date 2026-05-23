# Debate Log — Run 31 (2026-05-23)

Top 3 ideas ranked by impact: Idea 1 (GH #181 fix), Idea 2 (/moratorium-sprint), Idea 4 (Zapier security).

---

## Idea 1: Fix GH #181 — AMOUNT_TO_PLAN current-price entries + contradictory test

### Round 1

**Challenge:** billing.py is a HARD-STOP file in god-class-refactor_plan.md. Adding entries to
a production billing constant without a grill-me session violates the plan.

**Defend:** The HARD-STOP in god-class-refactor_plan.md applies to *splitting* billing.py
(Rule 9 god-class concern extraction). Fixing a missing dict entry is a surgical bug fix, not
a structural concern change. c72b535's commit message reads "Fix AMOUNT_TO_PLAN: correct
$150/$250 plan mappings" — the intent was already approved; only the execution was incomplete.
Two dict entries cannot cause regression to existing lookup logic. This is not a refactor,
it is a completion of a fix already merged to main.

### Round 2

**Challenge:** The test file asserts 15000 and 25000 should NOT be present. Doesn't that
suggest the intent was to remove these? Maybe $150 and $250 customers are handled by
metadata.plan, not by amount lookup.

**Defend:** Lines 38-44 of the test were written for issue #81, which was about WRONG entries
(`15000→professional` was the old bug — it incorrectly mapped $150 to professional when the
customer was actually on autopilot). The fix was to remove the wrong mappings AND add the
correct ones. c72b535 only did the first half. Evidence: CLAUDE.md explicitly documents
`autopilot=$150/mo` and `professional=$250/mo`. The _resolve_plan() function falls through to
amount-based lookup when metadata.plan is absent — which is common for tenants who subscribed
before metadata.plan was introduced. Without 15000 and 25000, these tenants silently return
None and lose their plan resolution.

### Round 3

**Challenge:** GH #181 was filed hours ago. Has anyone confirmed this is a live production
impact vs a theoretical gap?

**Defend:** The nightly review confirms the mapping is absent from AMOUNT_TO_PLAN (direct
code inspection, not a theoretical analysis). The impact is live: any webhook with `amount_total
= 15000` (no metadata.plan) returns `None` from `_resolve_plan()`, which causes the caller to
treat the tenant as unrecognized plan. CLAUDE.md documents current pricing; the gap is real.

**Verdict: SURVIVES → WINNER**
Evidence strong (3 independent sources: nightly review, code inspection, CLAUDE.md), fix is
surgical, CI is actively certifying wrong behavior, moratorium-safe.

---

## Idea 2: Invoke /moratorium-sprint (Items A+B+D)

### Round 1

**Challenge:** This has been the recommended winner 8+ consecutive runs (runs 25-30 cycling
through variations) without a single invocation. There is no new evidence that run 31 will
produce a different outcome.

**Defend:** The sprint is genuinely the highest-leverage single action. Pending drops from 6
to 2 = moratorium exits. The SKILL.md exists. The execution path is clear.

### Round 2

**Challenge:** If 8 runs of the same recommendation have zero success rate, the mechanism
is broken, not the recommendation. The subconscious loop should route around an evidenced
execution bottleneck rather than repeat the same ineffective signal.

**Defend:** The sprint is not rejected — it's acknowledged as the standing highest-leverage
action. The question is whether it should be the *winner for this run*. Given Idea 1 is a
fresher, higher-confidence, more urgent fix (live billing gap, CI wrong), /moratorium-sprint
should remain in the standing active direction but cede the winner slot.

### Round 3

**Challenge:** Does demotion compound? If sprint is never the winner, it's never implemented.

**Defend:** Sprint was the winner for runs 25-27 and was listed as standing active direction
in runs 28-30. It remains in active_directions. This run's winner slot goes to Idea 1 because
of its urgency. Demotion from winner to standing-action is not rejection.

**Verdict: WEAKENED → parking lot (standing action, not winner)**
Sprint remains the highest-leverage action. Run 31 winner slot goes to Idea 1 for urgency.
Escalation path: if Idea 1 is implemented but sprint still not invoked by run 32, recommend
redesigning sprint invocation mechanism (not another repeat winner).

---

## Idea 4: Zapier plan_status enforcement (GH #107)

### Round 1

**Challenge:** GH #107 is 23 days old in the parking lot with ROI 2.5 — the highest ROI item
in the parking lot. Why isn't this the winner if it's been ready for 23 days?

**Defend:** Moratorium is active with max_pending_approvals=2. Adding this to the winner queue
pushes pending to 7 (before sprint clears it). Run 16 debate killed it explicitly on this
basis. The situation hasn't changed.

### Round 2

**Challenge:** Run 30 (billing fix) was moratorium-exempt as S-effort, code-only. Zapier
fix is S-effort (~20 min), code-only, security. Same exemption should apply.

**Defend:** Run 30 was moratorium-exempt because it responded to a *live production bug just
fixed* (c72b535 same day). The exemption was driven by evidence freshness + production
incident context. Zapier has been in the parking lot 23 days with no escalating production
signal. The moratorium exemption applies to urgent evidence-fresh items, not backlog items.
Compared to Idea 1 (live billing gap, CI certifying wrong behavior, day-of discovery), Zapier
is lower urgency. Promote to next run after Idea 1 is resolved.

### Round 3

**Challenge:** Is 23 days "no escalating signal" or "chronic unaddressed security gap"?

**Defend:** No reported incidents. The bug-patterns entry has been stable (no new instances
found in nightly reviews). The fix path requires confirming exact path per bug-patterns.md
("Skeleton — confirm exact path before remediation"). Given Idea 1 is more urgent and
moratorium constraints are real, Zapier stays in parking lot. Promote to winner run 32 if
moratorium doesn't exit before then.

**Verdict: WEAKENED → parking lot**
Promote to winner in run 32 if moratorium exits after sprint invocation. Otherwise first
post-moratorium winner candidate (alongside AI-to-Human Handoff).

---

## Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| 1. Fix GH #181 + contradictory test | **SURVIVES → WINNER** | S-effort, live billing gap, CI wrong |
| 2. /moratorium-sprint | WEAKENED → standing action | 8+ recs, no new info, not rejected |
| 3. email_sequences split | Not debated (M-effort, lower urgency) | parking lot |
| 4. Zapier plan_status | WEAKENED → parking lot | promote run 32 |
| 5. Test coverage only | Not debated (subsumed by Idea 1) | |
