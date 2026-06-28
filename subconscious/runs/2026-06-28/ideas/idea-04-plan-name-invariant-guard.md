# Idea 04: Plan-Name Invariant Guard (check_project_invariants.py #3 Extension)

**Category:** Code Health  
**Effort:** ~30 minutes  
**Priority:** LOW (sequencing-blocked)

---

## The Opportunity

`check_project_invariants.py` Invariant #3 checks for retired plan names in plan-related code. Current check:

```python
RETIRED_PLAN_NAMES = ["foundation", "operations"]
```

These are the only two in the check. But the CLAUDE.md also calls out `free` as "internal lapsed/no-subscription state, never sold." Adding a guard for `free` appearing in plan-selection logic would catch future misuse.

Also: Invariant #3 only checks `backend/` — doesn't check `frontend/src/` for plan-name strings in UI components.

---

## Evidence

- `scripts/check_project_invariants.py` — Invariant #3 scans `backend/` only
- CLAUDE.md — "free = internal lapsed/no-subscription state, never sold"
- `frontend/src/pages/BillingPage.jsx` — plan name rendering, potential for drift

---

## Sequencing Block

This improvement is blocked until widget drift (Invariant #4) is resolved. Adding a new passing invariant while one existing invariant fails doesn't improve the overall exit code. Meaningful only after the `cp` fix.

---

## Why Not Winner

Sequencing-blocked. Low effort but blocked by widget drift resolution. Bonus item for the week after drift is fixed.
