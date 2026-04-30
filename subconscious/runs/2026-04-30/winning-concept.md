# Winning Concept — 2026-04-30

## Recommendation
Add JS Silent Catch Pre-commit Guard as Check 9 in `scripts/hooks/pre-commit` — grep staged `.js`/`.jsx` files for `.catch(() => null)` and `.catch(() => {})` patterns and block commits that contain them without an inline override comment.

## Why This, Why Now
This recommendation has been pending since run 3 (2026-04-11) — 19 days. The moratorium protocol in governance.json mandates that run 9 implement the oldest unimplemented winner rather than generate fresh ideas, and this is it. Today's evidence confirms both original violations persist: `MarketingDashboardPage.jsx:96` swallows analytics fetch errors silently and `LocalSEOPage.jsx:262` swallows SEO audit history silently. The 2026-04-23 bug-patterns.md entry for noshow_recovery CAN-SPAM (`except Exception: logger.debug(...)`) is the same root cause class — defensive exception swallowing that obscures production failures. The pre-commit hook already blocks the Python equivalent (bare-except); this closes the identical gap for JS/JSX.

## Implementation Sketch
1. **Audit staged files mechanic** — confirm pre-commit uses `git diff --cached --name-only` to enumerate staged files (it does, visible in existing checks).
2. **Add Check 9 to `scripts/hooks/pre-commit`** immediately after the Python checks section (after line ~232):
   ```bash
   # Check 9: JS silent catch — .catch(() => null) / .catch(() => {})
   printf "Check 9: JS silent catch guard... "
   JS_STAGED=$(git diff --cached --name-only | grep -E '\.(js|jsx)$')
   SILENT_CATCH_HITS=""
   if [ -n "$JS_STAGED" ]; then
     for f in $JS_STAGED; do
       hits=$(grep -nE '\.catch\(\s*\(\s*\)\s*=>\s*(null|\{\s*\})\s*\)' "$f" \
              | grep -v "ok-silent-catch" || true)
       if [ -n "$hits" ]; then
         SILENT_CATCH_HITS="$SILENT_CATCH_HITS\n  $f:\n$hits"
       fi
     done
   fi
   if [ -n "$SILENT_CATCH_HITS" ]; then
     echo -e "${RED}BLOCKED${NC}"
     echo -e "  Silent .catch found — exceptions swallowed without logging.$SILENT_CATCH_HITS"
     echo "  Fix: log the error, or add '// ok-silent-catch' if intentional graceful degradation."
     ERRORS=$((ERRORS + 1))
   else
     echo -e "${GREEN}OK${NC}"
   fi
   ```
3. **Fix the 2 existing violations** before wiring (or wire with `--no-verify`, fix immediately after):
   - `MarketingDashboardPage.jsx:96` — log the caught error or add `// ok-silent-catch` with comment explaining intent
   - `LocalSEOPage.jsx:262` — same
4. **Test the guard** — add a synthetic `.catch(() => null)` to a staged JS file, run `bash scripts/hooks/pre-commit`, confirm BLOCKED. Revert.
5. **Update `CLAUDE.md` Automation section** — add "Check 9: JS silent catch guard" to the pre-commit hook bullet list.
6. **Verify** — `bash scripts/hooks/pre-commit` passes on clean HEAD.

## What This Replaces
No previous active direction displaced. First JS-language guard in the pre-commit hook (all prior checks are Python or shell). Complements run 6 (migration naming) and run 8 (project invariants) as the third check in the pre-commit expansion series.

## Confidence
**HIGH** — Triple evidence backing: (1) violations confirmed today at 2 specific file:line locations, (2) same root cause class as a bug logged 2026-04-23 to bug-patterns.md, (3) pre-commit hook already implements the Python equivalent as clear precedent. Debate: SURVIVES all 4 challenges. Moratorium protocol is unambiguous. S-effort.

## Moratorium Status Note
After this run: 4 pending winners (runs 3, 4, 7, 8). Run 2 demoted to `implemented_unverified` — lead source analytics chart is live in `AnalyticsPage.jsx` lines 909–913. Moratorium lift condition (≤3 pending) requires implementing 1 more winner after run 3 closes. Recommend run 7 (Widget Sync Guard, S-effort) as the next target to lift the moratorium.
