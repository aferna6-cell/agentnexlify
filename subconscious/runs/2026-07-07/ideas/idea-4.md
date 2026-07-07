# Idea 4: Add Plan-Name Convention Guard as Pre-Commit Check 7 (P-001)

**Category:** Code Health (preventive)  
**Effort:** XS (pre-commit hook edit, 5–10 lines)  
**Autonomous:** YES — pre-commit hook edit (LOW-risk per nightly governance)  
**Source:** Parking lot P-001 (carried forward runs 72–80)  

---

## Evidence

- P-001 parking lot entry: "pre-commit doesn't enforce plan naming conventions. Low priority until next plan naming incident."
- Plan naming convention: `/plans/feature-name_plan.md` (kebab-case, `_plan.md` suffix)
- No recent violations detected (runs 72–80 scanning)
- Naming error would cause `scripts/check_plan_drift.py` ghost-ref false positives and mislead issue-to-pr-loop

## What to Add

Pre-commit Check 7: after the existing 6 checks (secrets, `__future__`, bare-except, etc.), add:

```bash
# Check 7: Plan file naming convention
staged_plans=$(git diff --cached --name-only | grep '^plans/')
if [ -n "$staged_plans" ]; then
  for f in $staged_plans; do
    if ! echo "$f" | grep -qE '^plans/[a-z0-9-]+_plan\.md$'; then
      echo "FAIL: Plan file '$f' violates naming convention (must be plans/kebab-name_plan.md)"
      exit 1
    fi
  done
fi
```

## Impact

- Prevents future plan naming violations before they reach the repo
- Protects `check_plan_drift.py` from false positives
- No false positives on current plan files (pre-verified naming is clean)
- XS: one bash block addition to `scripts/hooks/pre-commit`

## Why Not Winner This Run

No recent violations detected. Low urgency. SMS Dashboard label fix has higher immediate impact. Carry forward.

## Priority

Low. Implement when moratorium is fully cleared and no higher-priority autonomous items pending.
