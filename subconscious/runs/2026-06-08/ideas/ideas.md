# Ideas — Run 52 (2026-06-08)

Evidence window: 2026-06-05 → 2026-06-08

---

### Idea 1: Merge PR #183 — Close GH #181 billing fix (run 51 active winner)
**Evidence:** billing.py AMOUNT_TO_PLAN still missing `15000→autopilot` + `25000→professional` (confirmed live grep). test_billing_amount_to_plan.py lines 38-44 still have backwards assertions certifying the broken state. PR #183 has been open 15 days. Check 11 WARNING fires on every commit. Developer is NOW ACTIVE — 5 production PRs merged in 3 days (7a621a1, 2287f6b, abccdc3, 617b667, d20284f). Agent OS phase-3 polish (d20284f) landed yesterday — phase wrap signals context shift is possible.
**Action:** Verify PR #183 targets backend/routers/billing.py (not services/), contains both AMOUNT_TO_PLAN entries + corrected test assertions, confirm CI green, merge.
**Impact:** Closes GH #181 (51+ days), silences Check 11 WARNING, unblocks email_sequences.py god-class split (run 41, 1255L), removes the one standing CRITICAL billing gap.
**Category:** code_health

---

### Idea 2: Wire check_project_invariants.py into pre-commit as Check 10
**Evidence:** grep of scripts/hooks/pre-commit shows Check 11 present but NO Check 10. check_project_invariants.py exits 0 (pre-condition confirmed since run 49/8db33df). Item has been pending 41 days (run 8, 2026-04-25). Agent OS sprint just added 40+ new TypeScript + Python files — every future commit benefits from the guard. Developer is active and making rapid commits.
**Action:** Add 3 lines to scripts/hooks/pre-commit calling check_project_invariants.py as Check 10. ~5 min.
**Impact:** Blocks `tenant_id` naming violations, schema drift, em-dash in Python source on every future commit. Especially valuable now that Agent OS Python files are being rapidly added.
**Category:** code_health

---

### Idea 3: Add Agent OS widget-isolation regression test (invariant guard)
**Evidence:** 2287f6b (2026-06-07) fixed a critical production bug: "Agent OS no longer hijacks the public chat widget." The fix added test_os_inbound_bridge.py with 37 lines. But broader isolation invariant — Agent OS MUST NOT intercept any chat traffic for tenants without `os_enabled` — is the kind of rule that should be codified as an invariant test, not just a fix.
**Action:** Write a parametric test in test_os_inbound_bridge.py (or new file) asserting: for any request with `os_enabled=False`, Agent OS routing returns None / falls through. Covers the exact class of bug that was just fixed.
**Impact:** Prevents regression of a just-fixed critical bug as Agent OS is actively developed at high velocity.
**Category:** code_health

---

### Idea 4: Agent OS _orchestrator.ts integration test coverage audit
**Evidence:** _orchestrator.ts is 414 lines with 20+ specialist agents. Test surface: orchestrate.test.ts (75 lines), agent-os.isolation.test.ts (108 lines), agent-os.routing.test.ts (53 lines). 236 lines of tests for 414-line orchestration core + 20+ agents. Booking agent alone has booking/agent.ts (158 lines) + extract-slot.ts (54 lines). The orchestrator is the highest-risk new component.
**Action:** Assess coverage gaps in the orchestration path (classify → route → execute → deliver). If gap confirmed: write integration test for the booking agent end-to-end (most concrete path with extract-slot.ts now testable deterministically).
**Impact:** Prevents silent failures in the most complex new component as Agent OS is actively developed.
**Category:** code_health

---

### Idea 5: email_sequences.py god-class split (run 41 winner, unblocked post-PR #183)
**Evidence:** email_sequences.py confirmed 1255L (run 41 winner, 9+ days pending). god-class-splitter SKILL.md exists (e848b87). post-split-test-repair SKILL.md exists (d481799). The only stated prerequisite is GH #181 fix (billing.py). If PR #183 merges (Idea 1), this becomes immediately executable.
**Action:** After PR #183 merged: invoke /god-class-splitter on backend/routers/email_sequences.py → split into email_crud.py + email_enrollment.py + email_processor.py.
**Impact:** 1255L → ~3×420L. GH #112/#113 N+1 bugs become simpler. First production god-class split using the new skill.
**Category:** code_health

Note: Ideas 1 and 5 are sequenced — Idea 5 depends on Idea 1. Both recommended but only Idea 1 fits as this run's winner.
