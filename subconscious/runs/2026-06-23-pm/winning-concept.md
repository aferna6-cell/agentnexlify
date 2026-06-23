# Run 65 Winning Concept — 2026-06-23-pm

## Winner: Add plan-name guard Check 7 to check_project_invariants.py

**Category**: code_health  
**Confidence**: HIGH  
**AUTONOMOUS-EXECUTABLE**: YES  
**Moratorium impact**: NONE (pending_autonomous, not pending_approval)

---

## Why this wins

GH #292/#293 was active product breakage for 7 days before discovery, then took another 7 to implement. Every signup between 2026-06-16 and 2026-06-23 got wrong SMS limits and broken Zapier. Root cause: billing repricing updated plan_catalog.py but no automated check verified that the new plan names propagated to downstream service dicts.

The invariant: every plan in CURRENT_PAID_PLANS must appear in billing_reconciliation._PLAN_BASELINE_AI_TOKENS. This is the load-bearing billing surface — if a plan is missing here, the tenant gets no AI token budget.

check_project_invariants.py already enforces 6 invariants as pre-commit Check 13. Adding Check 7 to the script automatically gates it at commit time — zero additional wiring needed.

Sequencing block "after GH #292/#293 lands" is cleared: both bugs implemented today (57f2bb4d + 29ed1d43 + 3a958e5f). Check 7 will PASS on the current codebase.

---

## Implementation sketch

### File: `scripts/check_project_invariants.py`

Add a new function after the existing 6 checks:

```python
def check_plan_catalog_coverage() -> str:
    """Check 7: All CURRENT_PAID_PLANS appear in billing_reconciliation._PLAN_BASELINE_AI_TOKENS."""
    import ast

    catalog_path = ROOT / "backend" / "services" / "plan_catalog.py"
    recon_path = ROOT / "backend" / "services" / "billing_reconciliation.py"

    if not catalog_path.exists():
        return "FAIL: backend/services/plan_catalog.py not found"
    if not recon_path.exists():
        return "FAIL: backend/services/billing_reconciliation.py not found"

    # Parse CURRENT_PAID_PLANS from plan_catalog.py
    catalog_src = catalog_path.read_text()
    catalog_tree = ast.parse(catalog_src)
    current_paid_plans: set[str] = set()
    for node in ast.walk(catalog_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CURRENT_PAID_PLANS":
                    # frozenset({"chatbot", "agent_os"}) or set literal
                    if isinstance(node.value, ast.Call):
                        args = node.value.args
                        if args and isinstance(args[0], ast.Set):
                            for elt in args[0].elts:
                                if isinstance(elt, ast.Constant):
                                    current_paid_plans.add(elt.value)
                    elif isinstance(node.value, ast.Set):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant):
                                current_paid_plans.add(elt.value)

    if not current_paid_plans:
        return "FAIL: could not parse CURRENT_PAID_PLANS from plan_catalog.py"

    # Parse _PLAN_BASELINE_AI_TOKENS keys from billing_reconciliation.py
    recon_src = recon_path.read_text()
    recon_tree = ast.parse(recon_src)
    baseline_plans: set[str] = set()
    for node in ast.walk(recon_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_PLAN_BASELINE_AI_TOKENS":
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                baseline_plans.add(key.value)

    if not baseline_plans:
        return "FAIL: could not parse _PLAN_BASELINE_AI_TOKENS from billing_reconciliation.py"

    missing = current_paid_plans - baseline_plans
    if missing:
        return (
            f"FAIL: Plan(s) {sorted(missing)} in CURRENT_PAID_PLANS missing from "
            f"billing_reconciliation._PLAN_BASELINE_AI_TOKENS. "
            f"Add token baseline for each plan after any repricing."
        )

    return f"PASS: all CURRENT_PAID_PLANS {sorted(current_paid_plans)} covered in _PLAN_BASELINE_AI_TOKENS"
```

Then add to the `run_all_checks()` function (or equivalent entry point):
```python
results.append(("Check 7 — plan catalog coverage", check_plan_catalog_coverage()))
```

---

## Test assertion

After adding Check 7, `python3 scripts/check_project_invariants.py` should output:

```
Check 7 — plan catalog coverage: PASS: all CURRENT_PAID_PLANS ['agent_os', 'chatbot'] covered in _PLAN_BASELINE_AI_TOKENS
```

Regression test: temporarily remove `chatbot` from `_PLAN_BASELINE_AI_TOKENS`, run script → FAIL message shows. Restore.

---

## Nightly review path

This is the same class as Check 11 (061582c, autonomous 2026-05-29), Check 12 (ca3ce68, autonomous 2026-06-09), and Check 13 (bc91e97, autonomous 2026-06-17). Nightly review can implement Check 7 by:
1. Reading `scripts/check_project_invariants.py`
2. Appending the new function after the last existing check
3. Updating the check registry call
4. Running `python3 scripts/check_project_invariants.py` to verify PASS
5. Committing with message: `chore(invariants): add Check 7 — plan-catalog coverage guard`

No migration. No schema change. No new dependency. Pure stdlib (ast module).

---

## Why not broader?

Alternative was to check ALL plan-specific dicts (sms_rate_limiter._UNLIMITED_PLANS, api_key_auth._ALLOWED_PLANS). Rejected: those dicts intentionally exclude chatbot by product design. Checking them would require encoding product-intent logic ("chatbot is widget-only, so excluding from PREMIUM_PLANS is correct") inside the invariant script — fragile and opinionated. The billing baseline (PLAN_BASELINE_AI_TOKENS) is the one universal invariant: every paid plan must have a token budget.

Future runs can extend if new plan-specific dicts cause bugs.

---

## Governance notes for this run

**Major corrections applied this run:**
1. GH #292/#293 → status: implemented (commits 57f2bb4d + 29ed1d43, 2026-06-23)
2. GH #308 → status: implemented (commit 3a958e5f, 2026-06-23)
3. Both moratorium_override active_directions cleared
4. Moratorium remains active (true_pending_estimate ~7, exceeds max_pending_approvals=2)
5. New winner is AUTONOMOUS-EXECUTABLE (pending_autonomous) — does not worsen moratorium
