## Run 2026-06-22-pm — Winner

**Title:** Add Check 7 — Plan-Catalog Drift Guard to `scripts/check_project_invariants.py`

**Category:** code_health

**AUTONOMOUS-EXECUTABLE:** YES — nightly-commit-review can implement without human approval gate.

**Confidence:** HIGH

**Pre-condition:** Bonus A (57f2bb4 + 29ed1d4, 2026-06-22) has landed. `plan_catalog.py` with `CURRENT_PAID_PLANS` exists. Pre-condition was explicitly stated in run 64 Bonus B: "AUTONOMOUS-EXECUTABLE after Bonus A lands."

---

### Problem

Plan-name drift is a recurring bug class: GH #81, #181, #292, #293 — 4 incidents in 65 runs. The pattern is consistent: a new plan is added or renamed, `billing_reconciliation._PLAN_BASELINE_AI_TOKENS` (or a similar gate dict) is not updated, and production tenants get incorrect behavior.

`plan_catalog.py` now provides the canonical authority (`CURRENT_PAID_PLANS = frozenset({"chatbot", "agent_os"})`). `test_plan_catalog_coverage.py` guards premium gates at CI time (pytest). What's missing: a pre-commit gate that catches drift at commit time — 10x earlier feedback loop.

---

### Implementation Sketch

Append ~15 lines to `scripts/check_project_invariants.py` as Check 7:

```python
# Check 7: Every paid plan must have a token budget in billing_reconciliation
def check_plan_catalog_drift():
    """Guard: billing_reconciliation._PLAN_BASELINE_AI_TOKENS covers all CURRENT_PAID_PLANS."""
    from backend.services.plan_catalog import CURRENT_PAID_PLANS
    from backend.services import billing_reconciliation

    token_budgets = billing_reconciliation._PLAN_BASELINE_AI_TOKENS
    missing = [p for p in CURRENT_PAID_PLANS if p not in token_budgets]
    if missing:
        print(f"FAIL check_plan_catalog_drift: plans missing from _PLAN_BASELINE_AI_TOKENS: {missing}")
        print(f"  Add them to backend/services/billing_reconciliation.py")
        sys.exit(1)
    print(f"PASS check_plan_catalog_drift: all {len(CURRENT_PAID_PLANS)} paid plans have token budgets")
```

Add call `check_plan_catalog_drift()` to the main check runner block.

**Files touched:**
- `scripts/check_project_invariants.py` — append Check 7 function + call

**Test:** Run `python3 scripts/check_project_invariants.py` after adding. Should print `PASS check_plan_catalog_drift: all 2 paid plans have token budgets`.

**Regression test:** Temporarily add `"ghost_plan"` to `plan_catalog.CURRENT_PAID_PLANS` → script should exit 1 with specific error message. Then revert.

---

### Why This Wins

1. **Pre-condition confirmed met** — explicit Bonus B trigger from run 64: "after Bonus A lands". Bonus A = 57f2bb4 + 29ed1d4 (landed 2026-06-22).
2. **Moratorium-safe** — AUTONOMOUS-EXECUTABLE, does not add to pending_approval count. Moratorium constraint satisfied.
3. **Highest leverage per line** — ~15 lines, pure Python, no external deps, catches a 4-incident bug class permanently.
4. **Canonical source exists** — `plan_catalog.CURRENT_PAID_PLANS` is the frozenset authority. Import is stable.
5. **Layered defense** — complements `test_plan_catalog_coverage.py` (CI-time) by adding a pre-commit (commit-time) gate.

---

### Context: Moratorium Status Change

This run discovered both previously-pending winners are now implemented:
- GH #308 (run 59): `delete_key` exists at `backend/services/idempotency.py:96` — IMPLEMENTED by 3a958e5
- GH #292/#293 (run 62): `plan_catalog.py` + `test_plan_catalog_coverage.py` landed via 57f2bb4 + 29ed1d4 — IMPLEMENTED

With both pending_approval items resolved, pending_approval count drops to 0. **Moratorium exits this run.**

---

### Bonus A (parking lot, highest priority post-moratorium)

**AI-to-Human Handoff v1** — Idea 2. Highest-value customer gap (Critical rating, all 7 industries, 65+ days pending). Now unblocked by moratorium exit.

Action: Add explicit trigger detection in `widget_chat.py` (phrases: "speak to a human", "real person", "transfer me"). Write to `handoff_requests` table. Notify owner via `os_outbound_mirror.send_sms()`. Set conversation status to "handoff_pending". Estimated 1–1.5 day implementation.

This is now the #1 human implementation priority.

---

### RUN 66 MANDATE

If Check 7 is still unimplemented by Run 66: recommend again (AUTONOMOUS-EXECUTABLE, zero blocking dependencies).
