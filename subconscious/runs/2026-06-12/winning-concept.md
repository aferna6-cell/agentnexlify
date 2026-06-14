# Winning Concept — 2026-06-12

## Recommendation
Add pre-commit Check 13 — a FAIL-mode bash guard that rejects any staged Python file in `backend/` containing `from __future__ import annotations`.

## Why This, Why Now
PR #238 (auth.py split into auth_password_reset.py, auth_billing.py, auth_google.py) introduced `from __future__ import annotations` in 3 new router files within the same deploy cycle that run 55 targeted channels_instagram.py (1 file). The infection has spread to 4 files; without a guard, every future router split from the 14-target god-class-refactor plan will reproduce the same CLAUDE.md Critical Invariant #5 violation. Check 11 (billing-constant-guard, 22 lines bash, autonomous-implemented by nightly 061582c) and Check 12 (timing-safe guard, 20 lines bash, autonomous-implemented by nightly ca3ce68) are the exact same class — Check 13 belongs in the same pattern and has high autonomous delivery confidence.

## Implementation Sketch

```bash
# === Check 13: no `from __future__ import annotations` in FastAPI files ===
echo -n "Check 13: from __future__ import annotations guard... "
FUTURE_HITS=$(echo "$STAGED_FILES" | grep -E "^backend/.*\.py$" | \
    xargs grep -l "from __future__ import annotations" 2>/dev/null || true)
if [ -n "$FUTURE_HITS" ]; then
    echo -e "${RED}FAIL${NC}"
    echo "  CLAUDE.md Critical Invariant #5: 'from __future__ import annotations' in FastAPI files"
    echo "  causes Pydantic to resolve request bodies as strings → every endpoint returns 422."
    echo "  Files:"
    echo "$FUTURE_HITS" | head -5 | sed 's/^/    /'
    echo "  Fix: remove the 'from __future__ import annotations' line."
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}OK${NC}"
fi
```

Steps:
1. Insert bash block above the final `if [ $ERRORS -gt 0 ]` block in `scripts/hooks/pre-commit` (currently line ~275, after Check 12 block)
2. Use FAIL (ERRORS increment), not WARNING — this is a CLAUDE.md Critical Invariant, not a style guide
3. Scope to `backend/**/*.py` staged files only — frontend/widget files cannot have this issue
4. Update `subconscious/state/governance.json`: add run 56 winner to active_directions with `autonomous_executable: true`
5. Add AUTONOMOUS-EXECUTABLE label to winning-concept.md (this file) — nightly looks for this label

**AUTONOMOUS-EXECUTABLE**: Same mechanism as Check 11 and Check 12. Nightly review (2:37 AM) reads governance.json, sees pending_autonomous winner, executes bash insertion into pre-commit.

## What This Replaces
Run 56 does not supersede run 55 (fix channels_instagram.py + 10 em-dashes). Run 55 remains pending_autonomous. Check 13 is the systemic guard; run 55 fixes current violations. Proper execution order: Check 13 first (guard prevents new violations), then run 55 fix (clears existing violations).

## Confidence
HIGH — evidence of 100% recurrence on router splits (1 occurrence in run 55 → 4 occurrences 1 day later from a single PR). Bash insertion is proven autonomous class. Check 13 prevents infinite whack-a-mole on god-class-splitter targets.
