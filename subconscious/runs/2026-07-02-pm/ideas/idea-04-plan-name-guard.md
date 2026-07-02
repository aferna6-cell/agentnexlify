# Idea 04: Plan-Name Guard Check 7 (Pre-Commit)

**Category:** code_health  
**Effort:** XS (~10 min, 6-line bash)  
**Moratorium impact:** NONE — AUTONOMOUS-EXECUTABLE  
**Autonomous:** YES — same class as Check 11/12

## Evidence

- Parking lot since run 73 (3+ runs)
- No new urgency signal — check_project_invariants.py already guards retired plan names at runtime
- No production incident involving retired plan names since GH #292/#293 fix (2026-06-23)
- Run 76 explicitly parked this: "XS, AUTONOMOUS-EXECUTABLE, no urgency"

## Recommendation

Add Check 7 to `scripts/hooks/pre-commit`: grep staged Python files for retired plan names (`foundation`, `operations`). FAIL if found.

```bash
# Check 7: Retired plan name guard
RETIRED_PLANS="foundation|operations"
if git diff --cached --name-only | grep -q "\.py$"; then
    if git diff --cached -- "*.py" | grep -qE "^\+.*(${RETIRED_PLANS})"; then
        echo "PRE-COMMIT FAIL: retired plan name in staged Python files"
        exit 1
    fi
fi
```

## Why this is weak

- Parking lot item with 0 urgency for 3+ runs
- `check_project_invariants.py` already guards this at runtime (Check 5)
- Pre-commit guard is belt-and-suspenders at best
- No production incident since last plan name fix

## Score

| Dimension | Rating |
|-----------|--------|
| Evidence quality | LOW — no new incident |
| Impact | LOW — already guarded at runtime |
| Effort | XS |
| Novelty | LOW — parking lot 3+ runs |
| Moratorium | NONE |

**Total: PARKING LOT — no new trigger, run 76 already parked it**
