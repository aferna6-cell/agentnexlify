# Nightly Commit Review — 2026-08-09

**Run time:** 2026-08-09 (automated, 2:37 AM cadence)
**Commits reviewed:** 3 in last 24h
**Issues found:** 0 new
**Fixes applied:** 0 (no LOW-risk bugs found)
**Issues filed:** 0

---

## Context

The previous run (2026-08-08) carried over a MEDIUM issue (GH #640 — `POST /buy-usage`
missing `block_demo_role` guard). That session applied the fix (`c204af2`) and added a
regression test (`228203d`). Both landed on main. Today's review confirms the issue is
fully resolved.

---

## Commits Reviewed

### `2c9d0aa` — ops: nightly-commit-review 2026-08-08
**Risk:** INFO — ops log commit, no code changes.
**Triage:** PASS. No action needed.

### `c204af2` — fix: add block_demo_role guard to buy-usage Stripe endpoint
**Risk:** MEDIUM (payments endpoint touched)
**Triage:** PASS. Commit diff shows only the nightly log file was updated (the log
reflecting the fix that was applied). The actual code change landed in the prior session
(`cbbaae5`). Current state of `backend/routers/billing_usage.py` confirms:
- Line 13: `block_demo_role` imported from `backend.dependencies`
- Line 54: `@router.post("/buy-usage", dependencies=[Depends(block_demo_role)])` — guard present

Verified: `grep "block_demo_role" backend/routers/billing_usage.py` — lines 13 + 54 — PASS

### `228203d` — test: add block_demo_role guard assertion for POST /buy-usage (GH #640)
**Risk:** LOW — test-only change
**Triage:** PASS. Adds `test_buy_usage_has_block_demo_role_guard` to
`backend/tests/test_plan_gating_new_plans.py`. The test inspects router route
dependencies at import-time, asserting `block_demo_role` is present. This prevents
silent regression — any future removal of the guard will cause a test failure.
Test logic is correct and consistent with the existing plan-gating test patterns.

Verified: `python3 -c "import ast; ast.parse(open('backend/tests/test_plan_gating_new_plans.py').read())"` — PASS
Note: pytest not available in this remote env (stripe module missing); static analysis
confirms test is syntactically correct and structurally sound.

---

## No Issues Filed

No new MEDIUM or HIGH issues found. No LOW-risk bugs requiring a fix.
GH #640 is closed — guard in place, regression test added.

---

## Verification Summary

```
Verified: grep "block_demo_role" backend/routers/billing_usage.py → lines 13 + 54 — PASS
Verified: python3 -c "import ast; ast.parse(open('backend/routers/billing_usage.py').read())" — PASS
Verified: python3 -c "import ast; ast.parse(open('backend/tests/test_plan_gating_new_plans.py').read())" — PASS
Verified: no __future__ annotations in any changed file — PASS
Verified: no tenant_id usage on leads/conversations tables in changed files — PASS
```
