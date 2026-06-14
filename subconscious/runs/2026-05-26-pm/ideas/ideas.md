# Ideas — Run 35 (2026-05-26-pm)

## Evidence Digest

GH #181 billing fix still NOT implemented — 5th consecutive recommendation, governance CRITICAL threshold fires. billing.py missing 15000→autopilot + 25000→professional; test_billing_amount_to_plan.py:38-44 backwards assertions still active. Sprint Items A/B/D all MISSING (moratorium day 22+). Morning digest surfaces new evidence: PR #182 "Split invoices.py god class into 4 service modules + router" (3 days, Draft) is the first production god-class split since skill creation (e848b87). email_sequences.py confirmed 1255L with 3 independent concerns (CRUD/enrollment/processor). 5 stale Dependabot PRs (#11-15, 42 days). god-class-splitter SKILL.md created yesterday. No production code commits today. Pending approvals remain at 9+.

What changed: (1) PR #182 exists as first post-skill god-class split; (2) GH #181 hits 5-consecutive threshold; (3) god-class-splitter validated via e848b87 and ready for production use.

---

### Idea 1: GH #181 Critical Escalation — Formally Halt Repetition Loop

**Evidence:** 5th consecutive recommendation. billing.py:264 missing 15000+25000 confirmed (direct inspection). test_billing_amount_to_plan.py:38-44 backwards assertions still live. c72b535 and 1eaaeec both failed. Governance CRITICAL threshold fires (run 34 implementation_lag_warning note: "5-consecutive-run threshold exceeded — escalate to critical").

**Action:** Add GH #181 to `rejected_paths` with status "recommendation_exhausted_mechanism_change_required" — document 5 on-record recommendations, halt future recs until human explicitly implements or rejects, note that billing.py fix is now a standing critical action (not a winner candidate) until actioned.

**Impact:** Unsticks recommendation loop. Prevents run 36 from being another GH #181 echo with zero new evidence. Forces a binary decision (implement/reject) rather than indefinite deferral.

**Category:** workflow

---

### Idea 2: Invoke /god-class-splitter on email_sequences.py

**Evidence:** email_sequences.py is 1255L (confirmed). Three independent concerns identifiable from top-level structure: (1) sequence + step CRUD (lines 60-676), (2) enrollment logic (lines 96-253, _enroll_lead, enroll_lead_in_sequences, list_enrollments), (3) sequence processor (lines 875-1243, process_sequences, run_sequence_processor). GH #112/#113 open since 2026-05-02 for N+1 queries in list_enrollments + list_sequences — these are in concern (2) and would be easier to fix post-split in an isolated module. god-class-splitter SKILL.md created yesterday (e848b87). god-class-refactor_plan.md tracks 29 remaining backend targets.

**Action:** Invoke /god-class-splitter on email_sequences.py — split into email_crud.py (sequence/step management endpoints), email_enrollment.py (enroll_lead, auto-enroll, list_enrollments), email_processor.py (process_sequences, run_sequence_processor, _update_send_status).

**Impact:** 1255L → 3 focused modules (~300-450L each). N+1 issues in #112/#113 become simpler to fix in isolated enrollment service. First production validation of god-class-splitter SKILL.md. Passes Rule 9 (>600L file → split first before adding).

**Category:** code_health

---

### Idea 3: Batch Merge 5 Stale Dependabot PRs (#11-15)

**Evidence:** Morning digest lists 5 Dependabot PRs open 42 days: #11 (actions/cache 4→5), #12 (actions/setup-python 5→6), #13 (peter-evans/create-pull-request 6→8), #14 (actions/setup-node 4→6), #15 (actions/upload-artifact 4→7). All are GitHub Actions version bumps with no breaking changes. PR #186 also open (1 day, @typescript-eslint/parser 8.58→8.60).

**Action:** Review all 5 stale PRs + #186, confirm no breaking API changes, merge in one batch session (~5 min).

**Impact:** Clears 42-day-old security/dependency drift. GitHub Actions security hygiene. Reduces PR list noise. Unblocks CI if any of these are referenced in workflows. Moratorium-safe (no pending approvals impacted).

**Category:** operational

---

### Idea 4: Wire Billing-Constant-Guard as Pre-commit Check 11

**Evidence:** Parking lot since run 33 (ROI 2.1). Skill discovery 2026-05-25 documented triple-fix pattern (c72b535 + 1eaaeec + 1553bf7 = 3 commits on same billing bug class). GH #181 is now 5 consecutive — no automated guard exists to prevent the next mapping gap. Check 9 (JS silent catch) was added autonomously by nightly review (72f8204). Check 10 (check_project_invariants) is Sprint Item A. Check 11 (billing constants) would be a fresh addition.

**Action:** Add pre-commit Check 11 (~10 lines bash) to `scripts/hooks/pre-commit` — parse billing.py AMOUNT_TO_PLAN, validate {9900, 15000, 25000, 89900} are all present, FAIL with actionable message if any missing.

**Impact:** Prevents future billing mapping gaps from reaching CI. 1eaaeec (failed fix) would have been caught by Check 11 at pre-commit stage. Autonomously executable by nightly review (LOW-risk additive bash). Complements GH #181 fix (point fix + systemic guard).

**Category:** code_health

---

### Idea 5: Recommend Review + Merge of PR #182 (invoices.py god-class split)

**Evidence:** PR #182 "Split invoices.py god class into 4 service modules + router" open 3 days, Draft. Morning digest flags it as needing review. First draft PR that applies the god-class split pattern post-skill creation. Skill SKILL.md defines a 12-step checklist; PR #182 may have followed it or may have gaps (prior splits required follow-up commits to repair stale importers).

**Action:** Verify PR #182 against god-class-splitter 12-step checklist; document any gaps; recommend merge if it passes Steps 6 (all importers updated), 9 (tests pass), 10 (no stale refs), 11 (smoke tests written).

**Impact:** Closes draft PR. First post-skill-creation production validation of the checklist. Identifies gaps in SKILL.md for next run.

**Category:** code_health / workflow
