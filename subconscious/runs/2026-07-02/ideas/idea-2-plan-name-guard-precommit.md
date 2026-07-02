# Idea 2: Plan-Name Guard Pre-Commit Hook (Check 14)

**Category:** code_health  
**Effort:** XS  
**AUTONOMOUS-EXECUTABLE:** YES

## Evidence

CLAUDE.md §Plan names: `foundation` and `operations` listed as "Retired names, never use." No pre-commit check enforces this. Pattern proven: Checks 9–13 all shipped autonomously via nightly review. GH #292/#293 (2026-06-23) showed plan name dict errors slip through — `chatbot`/`agent_os` missing from dicts, causing wrong SMS limits for all paid tenants post-repricing.

## Action

Append ~10-line bash block to `scripts/hooks/pre-commit` after Check 13:

```bash
# Check 14: Retired plan name guard
echo "CHECK 14: Retired plan names..."
if grep -r --include="*.py" "foundation\|operations" backend/ | grep -v "^Binary\|#\|test_\|\.pyc" | grep -q "plan"; then
  echo "FAIL: Retired plan name (foundation/operations) in plan-related code"
  exit 1
fi
echo "PASS"
```

## Expected Impact

- Catches retired plan name usage before commit
- Zero human queue impact (AUTONOMOUS-EXECUTABLE, nightly applies)
- Consistent with Check 9–13 pattern

## Why Debated

No recent incident documents a retired plan name appearing in new code. Preventive, not reactive.
