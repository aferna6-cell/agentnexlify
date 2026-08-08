# Nightly Commit Review — 2026-08-08

**Run time:** 2026-08-08 (automated, 2:37 AM cadence)
**Commits reviewed:** 0 on main in last 24h (see note below)
**Issues found:** 1 carry-over MEDIUM (GH #640 — fix never landed on main)
**Fixes applied:** 1 LOW (unused import removed from billing_usage.py)
**Issues filed:** GH #640 reopened with updated status

---

## Key Finding — Previous Fix Never Merged to Main

The 2026-08-07 nightly review session found and applied fixes to `billing_usage.py`
(unused import + missing `block_demo_role` guard). However, that session ran with
**HEAD detached from `refs/heads/main`**. The commits (`97e1044`, `cbbaae5`, `7dff08b`)
were orphaned and never pushed to `origin/main`.

The 2026-08-07 log said "Fixed directly" — correct about what the session did, incorrect
that it landed in production. The owner closed GH #640 believing the fix was applied.

**Actual state of main as of 2026-08-08:**
- `POST /api/v1/billing/buy-usage` — **no `block_demo_role` guard** (MEDIUM — demo users can reach $24.99 Stripe checkout)
- `current_period_month` — unused import still present (LOW — fixed this run)

---

## Commits on Main (Last 24h)

None. Most recent commit on main: `fc2dd7d` (subconscious run 2026-08-06-pm, [skip ci]).

---

## Actions This Run

### LOW fix applied — unused import removed
**File:** `backend/routers/billing_usage.py`
**Change:** Removed unused `current_period_month` from `ai_usage_guard` import.
`get_ai_usage_status` is the only symbol used from that module; `current_period_month`
was imported but never referenced.
**Risk:** LOW. Import-only change, no logic touched.
**Status:** Committed to main.

### GH #640 — reopened
**Issue:** `MEDIUM: buy-usage Stripe endpoint missing block_demo_role guard`
**Action:** Reopened with updated body explaining the fix was on a detached HEAD
and never merged. Requires human review to apply — nightly review does not touch
payments code without explicit approval.
**URL:** https://github.com/aferna6-cell/agentnexlify/issues/640

---

## Verification

```
Verified: python -c "import ast; ast.parse(open('backend/routers/billing_usage.py').read())" — PASS
Verified: grep "current_period_month" backend/routers/billing_usage.py — empty (import removed)
Verified: grep "block_demo_role" backend/routers/billing_usage.py — not present (human review required)
```

---

## Outstanding (Human Action Required)

| Issue | Risk | File | Fix |
|-------|------|------|-----|
| GH #640 | MEDIUM | `backend/routers/billing_usage.py:51` | Add `dependencies=[Depends(block_demo_role)]` to `@router.post("/buy-usage")` and import `block_demo_role` from `backend.dependencies` |
