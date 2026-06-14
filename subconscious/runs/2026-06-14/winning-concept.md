# Winning Concept — 2026-06-14

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Wire `check_project_invariants.py` into pre-commit as Check 10, and add Check 13 (from __future__
bash guard) in the same commit — locking the invariant sweep achieved by 3234597 as a permanent
commit-time gate.

## Why This, Why Now
`check_project_invariants.py` exits 0 for the first time ever (verified 2026-06-14 live run).
The 50-commit sprint 3234597 cleared all 6 invariant violations: `from __future__` (3 router
files), widget drift, and em-dash violations. Without wiring the script to pre-commit, the next
god-class split or router addition will reintroduce violations undetected — exactly what happened
three times in 11 days with `from __future__` before 3234597 fixed them. Run 22 (pending_autonomous,
51 days) and run 42 (de-coupled Item A) both target Check 10; both are now unblocked. The window
is today — before the next feature PR lands.

## Implementation Sketch

```bash
# Step 1: Add Check 10 to scripts/hooks/pre-commit (after Check 12 block, ~line 298):
cat >> scripts/hooks/pre-commit << 'PATCH'

# Check 10: Project invariants (check_project_invariants.py)
echo -n "Check 10: Project invariants... "
if python3 scripts/check_project_invariants.py > /tmp/invariant_out 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}BLOCKED${NC}"
    cat /tmp/invariant_out
    ERRORS=$((ERRORS + 1))
fi
PATCH

# Step 2: Add Check 13 (from __future__ bash guard) immediately after Check 10:
cat >> scripts/hooks/pre-commit << 'PATCH'

# Check 13: from __future__ import annotations in FastAPI router files
echo -n "Check 13: from __future__ import annotations guard... "
STAGED_PY=$(git diff --cached --name-only | grep -E '^backend/.*\.py$' || true)
FUTURE_HITS=""
if [ -n "$STAGED_PY" ]; then
    for f in $STAGED_PY; do
        if [ -f "$f" ]; then
            hits=$(grep -n "^from __future__ import annotations" "$f" \
                   | grep -v "# ok-future-annotations" || true)
            if [ -n "$hits" ]; then
                FUTURE_HITS="$FUTURE_HITS\n  $f: $hits"
            fi
        fi
    done
fi
if [ -n "$FUTURE_HITS" ]; then
    echo -e "${RED}BLOCKED${NC}"
    echo -e "  'from __future__ import annotations' breaks FastAPI/Pydantic at runtime (all endpoints 422)."
    echo -e "  Remove the import. See CLAUDE.md Critical Invariant #5.$FUTURE_HITS"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}OK${NC}"
fi
PATCH

# Step 3: Verify — run pre-commit manually on empty staged set:
bash scripts/hooks/pre-commit
# Expected: Check 10 → OK, Check 13 → OK

# Step 4: Commit
git add scripts/hooks/pre-commit
git commit -m "fix(pre-commit): add Check 10 (invariant gate) + Check 13 (from __future__ guard)"
```

Notes:
- Check 10 uses `/tmp/invariant_out` temp file to capture script output on FAIL.
- Check 13 scans only staged backend Python files (not entire codebase) for performance.
- Both checks use existing `ERRORS` counter and `GREEN`/`RED` color vars.
- `# ok-future-annotations` comment bypass (consistent with `# ok-silent-catch` pattern).

## What This Replaces
- Run 22 active_direction (pending_autonomous → implemented after execution)
- Run 42 active_direction (pending_autonomous → implemented after execution)
- Run 56 bonus: Check 13 implemented in same commit as Check 10

## Confidence
HIGH — evidence is concrete (check_project_invariants.py exits 0 confirmed live), implementation
is AUTONOMOUS-EXECUTABLE (same bash pattern as Check 11/12), debate survived all 3 challenge
rounds, no governance restrictions apply (pending_autonomous does not increase pending_approval count).
