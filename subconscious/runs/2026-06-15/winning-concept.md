# Winning Concept — 2026-06-15

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Add pre-commit Check 13 — a FAIL-mode bash guard that blocks any staged Python file in `backend/` from containing `from __future__ import annotations`.

## Why This, Why Now
Run 56 (2026-06-12) won this same recommendation but nightly has not yet executed it — pre-commit still ends at Check 12, confirmed by direct inspection of `scripts/hooks/pre-commit`. Runs 55 and 57 (fixing em-dashes + from __future__ violations + widget sync) are now IMPLEMENTED: `check_project_invariants.py` passes all 6 checks clean for the first time since run 49. But without Check 13, the invariant is maintained only by human discipline. Evidence confirms 100% recurrence on every router split: PR #238 (auth.py split) introduced 3 new `from __future__ import annotations` violations within 24h of run 55 fixing them. 98 router files exist; upcoming god-class splits (email_sequences.py, Home.jsx, others) each carry this risk. The fix is 10 lines of bash, autonomous-executable by nightly, and consumes zero human dev time.

## Implementation Sketch

1. Open `scripts/hooks/pre-commit`
2. After the existing Check 12 block (ends around line 305), add:

```bash
# Check 13: from __future__ import annotations guard in FastAPI files
echo -n "Check 13: from __future__ import annotations guard... "
FUTURE_STAGED=$(git diff --cached --name-only | grep "^backend/.*\.py$" || true)
FUTURE_HITS=""
if [ -n "$FUTURE_STAGED" ]; then
    for f in $FUTURE_STAGED; do
        if [ -f "$f" ]; then
            hits=$(grep -n "from __future__ import annotations" "$f" \
                   | grep -v "ok-future-annotations" || true)
            if [ -n "$hits" ]; then
                FUTURE_HITS="$FUTURE_HITS\n  $f:\n$hits"
            fi
        fi
    done
fi
if [ -n "$FUTURE_HITS" ]; then
    echo -e "${RED}BLOCKED${NC}"
    echo -e "  from __future__ import annotations found — FastAPI uses runtime annotation evaluation."
    echo -e "  This breaks Pydantic request body parsing and causes 422 on all endpoints in the file.$FUTURE_HITS"
    echo "  Fix: remove the import. Use quoted type hints ('MyType') if forward refs needed."
    echo "  See CLAUDE.md Critical Invariant #5."
    echo "  Bypass (only if non-FastAPI file): add '# ok-future-annotations' comment"
    ERRORS=\$((ERRORS + 1))
else
    echo -e "${GREEN}OK${NC}"
fi
```

3. Verify the block parses: `bash -n scripts/hooks/pre-commit`
4. Commit: `git add scripts/hooks/pre-commit && git commit -m "fix(pre-commit): Check 13 — block from __future__ import annotations in FastAPI files (CLAUDE.md CI #5)"`

## What This Replaces
Run 56 active_direction (pending_autonomous). Check 13 closes the run 56 recommendation; this run confirms and re-targets it. Governance correction this run: runs 55 and 57 status → implemented (check_project_invariants passes clean).

## Confidence
HIGH — evidence is concrete (pre-commit ends at Check 12, verified by direct read; 100% recurrence rate documented; autonomous execution of bash blocks is well-precedented: Check 11 by 061582c, Check 12 by ca3ce68). AUTONOMOUS-EXECUTABLE: nightly reads governance.json, sees pending_autonomous winner with AUTONOMOUS-EXECUTABLE label, applies the patch.
