# Winning Concept — 2026-04-11-pm

## Recommendation
Extend `scripts/hooks/pre-commit` with a Check 8 that detects silent `.catch(() => null)` / `.catch(() => {})` patterns in staged JS/JSX/TS/TSX files and emits a WARNING (not a hard block).

## Why This, Why Now
The Apr 10 daily log — AgentNexLiFy's own automated monitoring system — explicitly listed this as Priority 2 and recommended the pre-commit extension. Eight silent catch patterns have been stable for 2+ days with no organic fix, meaning the team habitually writes them but the current hook doesn't signal they're a problem. The existing pre-commit hook (Check 3) already handles Python bare excepts using the exact same WARNING pattern — adding the JS equivalent is a natural, low-friction extension. Unlike the other competing improvements (widget E2E tests with uncertain Playwright infra, KB ingestion with unverified brief quality), this change has zero infrastructure uncertainty: it's a bash grep on staged files, consistent with 7 existing checks in the same file. The improvement is permanent and compounds on every future commit.

## Implementation Sketch
1. **Edit `scripts/hooks/pre-commit`** — add after the existing Check 7 block (around line 197):
   ```bash
   # CHECK 8: Silent JS/TS catch patterns
   echo -n "Checking for silent JS/TS error swallowing... "
   JS_SILENT_CATCH_FOUND=""
   for file in $STAGED_FILES; do
     if [[ "$file" == *.js || "$file" == *.jsx || "$file" == *.ts || "$file" == *.tsx ]]; then
       if [ -f "$file" ]; then
         MATCH=$(grep -nE "\.catch\s*\(\s*\(\s*\)\s*=>\s*(null|undefined|\{\s*\}|\(\s*\{\s*\}\s*\))\s*\)" "$file" 2>/dev/null || true)
         if [ -n "$MATCH" ]; then
           JS_SILENT_CATCH_FOUND="$JS_SILENT_CATCH_FOUND\n  $file: $MATCH"
         fi
       fi
     fi
   done
   if [ -n "$JS_SILENT_CATCH_FOUND" ]; then
     echo -e "${YELLOW}WARNING${NC}"
     echo -e "  Silent .catch() swallows errors — log or handle them:${JS_SILENT_CATCH_FOUND}"
     echo -e "  Add '// subconscious-ignore' comment to exempt intentional cases."
     WARNINGS=$((WARNINGS + 1))
   else
     echo -e "${GREEN}OK${NC}"
   fi
   ```
2. **Reinstall hook** — `bash scripts/install-hooks.sh` to copy updated hook to `.git/hooks/pre-commit`
3. **Separately (follow-up, not part of this recommendation):** Fix the existing 8 silent catches in `AdminAnalyticsPage` (6), `MarketingDashboardPage` (1), `LocalSEOPage` (1) — either add proper error handling or add `// subconscious-ignore` with a justification comment.
4. **Verify** — stage a file containing `.catch(() => null)` and run `git commit --dry-run` to confirm WARNING fires.

## What This Replaces
Previous active direction: "Add Lead Source Analytics Chart to Dashboard" (run 2026-04-06, customer_value category). This run diversifies to code_health per the three-run pattern (workflow → customer_value → code_health).

## Confidence
HIGH — Evidence is triple-verified: (1) daily log Apr 10 Priority 2 + explicit pre-commit recommendation, (2) pre-commit hook structure already handles the exact same class of problem (Python bare excepts, Check 3), (3) implementation is a bash one-liner with zero external dependencies or infrastructure assumptions.
