### Idea 1: Add Check 7 — Plan-Catalog Drift Guard to check_project_invariants.py

**Evidence:**
- Runs 62–64 all included this as Bonus B: "AUTONOMOUS-EXECUTABLE after Bonus A lands."
  Bonus A (57f2bb4 + 29ed1d4, 2026-06-22) has now landed.
- `plan_catalog.py` (3d4c7db, 2026-06-22) defines `CURRENT_PAID_PLANS = {"chatbot", "agent_os"}` — canonical authority now exists.
- `test_plan_catalog_coverage.py` guards premium gates in pytest only (CI-time). Pre-commit fires at commit-time, 10x earlier feedback.
- Bug class (GH #81, #181, #292, #293) has 100% recurrence on every pricing change. 4 incidents in 65 runs.
- `billing_reconciliation._PLAN_BASELINE_AI_TOKENS` has both plans (chatbot: 800k, agent_os: 5M) — this check would be a regression guard against future omission.

**Action:**
Append ~15 Python lines to `scripts/check_project_invariants.py` as Check 7:
- Import/define `CURRENT_PAID_PLANS = {"chatbot", "agent_os"}` (or import from plan_catalog.py)
- Assert that both names appear in `billing_reconciliation._PLAN_BASELINE_AI_TOKENS` (all paid plans need token budgets)
- Print `PASS` or exit 1 with specific plan + file

**Impact:**
- Prevents next repricing (or new plan addition) from silently breaking token budgets
- AUTONOMOUS-EXECUTABLE by nightly review (same class as prior Check 10–13)
- Does not add to pending_approval count (no human approval gate needed)

**Category:** code_health
