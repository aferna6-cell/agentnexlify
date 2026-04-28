# Winning Concept — 2026-04-28-pm

## Recommendation
Add pre-commit Check 9 to `scripts/hooks/pre-commit` — a JS silent catch guard that blocks `.catch(() => null)` and `.catch(() => {})` patterns in staged JS/JSX/TS/TSX files — fully closing Run 3's recommendation (2026-04-11, 17 days).

## Why This, Why Now
Run 9's partial implementation (e68677a, 2026-04-28) patched all 4 active violations with logging but did not add the guard that prevents future violations. The same 3 violations existed undiscovered for 14+ days before the subconscious loop found them — without a guard, any future commit can silently reintroduce the same pattern. The pre-commit hook already has an established 8-check pattern (Check 6 blocks Python bare-excepts, Check 8 blocks dropped-column queries); Check 9 is the same mechanism for JS. Adding it takes ~8 lines of bash and closes the run 3 winner fully, dropping pending approvals from 4 to 3 (runs 4, 7, 8) and lifting the moratorium.

## Implementation Sketch
1. Open `scripts/hooks/pre-commit` at the end of the checks section (after line ~220, before the error-count exit block).
2. Add:
   ```bash
   # CHECK 9: JS silent catches (.catch(() => null) or .catch(() => {}))
   echo -n "Checking for JS silent catch handlers... "
   JS_SILENT=$(git diff --cached --name-only | grep -E '\.(jsx?|tsx?)$' | \
     xargs grep -lE '\.catch\(\(\)\s*=>\s*(null|\{\}\s*)\)' 2>/dev/null || true)
   if [ -n "$JS_SILENT" ]; then
     echo -e "${RED}BLOCKED${NC}"
     echo "  Silent JS catch detected in: $JS_SILENT"
     echo "  Replace .catch(() => null) with at minimum: .catch((err) => console.warn(...))"
     ERRORS=$((ERRORS + 1))
   else
     echo -e "${GREEN}OK${NC}"
   fi
   ```
3. Run `bash scripts/hooks/pre-commit` on clean HEAD — confirm passes.
4. Create a test file with `.catch(() => null)`, stage it, run hook — confirm BLOCKED.
5. Update governance.json: run 3 status → `implemented` (from `implemented_weakened`). Recalculate moratorium: 3 pending (runs 4, 7, 8) → moratorium lifted.

## What This Replaces
Run 3's active_directions entry "JS Silent Catch Pre-commit Guard" (2026-04-11) — already partially fulfilled by e68677a. This is the final piece.

## Confidence
**HIGH** — Direct completion of a well-defined pending item. S-effort (~8 lines bash). Pattern established by Checks 6 and 8. Evidence: 14-day undiscovered violations, e68677a confirmed violations exist, regex pattern validated against known violation sites.

## Moratorium Impact
After implementation: run 3 = `implemented`. Pending count: 3 (runs 4, 7, 8). Lift condition (≤ 3) met → **moratorium lifted**. Next run may generate fresh ideas.
