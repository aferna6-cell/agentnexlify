# Idea 2 — Add plan-name invariant guard Check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE, Bonus A from run 65)

**Score:** 6.8 / 10
**Effort:** S (~10 min)
**Category:** code_health
**Autonomous:** YES (but SEQUENCING-BLOCKED until run 65 widget drift fix lands)
**Status:** Parking Lot / Bonus A from run 65

## Evidence

- check_project_invariants.py currently guards: client_id discipline, lead status field, areas_of_interest, widget byte-sync, from __future__ annotations, direct SDK calls
- Missing: plan name guard (chatbot / agent_os are current; retired: foundation, operations, growth, autopilot, professional, enterprise)
- After 2-plan repricing (2026-06-16), risk of old plan names silently appearing in new code is real
- test_plan_gating_new_plans.py created 2026-06-23 guards billing_reconciliation.py but not general codebase
- Bonus A in run 65 winning-concept.md; originally parking lot from run 61

## Why it doesn't win run 66

**Sequencing blocked.** check_project_invariants.py currently exits 1 due to run 65 violations. Adding Check 7 BEFORE run 65 is implemented would:
1. Pre-commit remains blocked regardless
2. Can't verify Check 7 passes without first clearing existing failures
3. Run 65 fix must land first → Check 7 is a follow-on

**Correct sequence:** run 65 lands (check exits 0) → add Check 7 → check exits 0 again → confirm.

## Promotion path

Becomes run 67 candidate once run 65 is confirmed implemented. AUTONOMOUS-EXECUTABLE. Estimated 1 cycle.
