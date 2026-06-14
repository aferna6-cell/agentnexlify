# Winning Concept — 2026-04-30-pm (Run 11)

## Recommendation
Fix AdminAnalyticsPage.jsx:117-122 (add console.warn to 6 silent catches), then add JS Silent Catch as Check 9 in `scripts/hooks/pre-commit` — completing the run 3 recommendation with updated evidence.

## Why This, Why Now

**Governance correction:** The original violations cited in run 3 (MarketingDashboardPage.jsx:96 + LocalSEOPage.jsx:262) were FIXED by `e68677a` (`fix(silent-errors): add logging to 4 bare-exception/silent-catch handlers`, ~7 days ago). They no longer violate. This is a partial implementation of the spirit of run 3 — someone fixed the individual violations.

**But the pattern recurred immediately.** AdminAnalyticsPage.jsx:117-122 now has 6 `.catch(() => null)` calls inside a `Promise.all`, with zero logging. Admin dashboard silently swallows failures for overview, weekly growth, monthly growth, plan distribution, revenue trends, and industry breakdown. The fix-without-a-guard cycle is confirmed: patches don't hold, the pattern migrates to new files.

**Sprint timing.** `plans/onboarding-v2_plan.md` was created today with 21 issues. The onboarding sprint is about to generate more JS/JSX files. Installing the guard before the sprint means all 21 issues are covered automatically.

**Pre-commit gap.** Check 3 in the hook covers Python bare-excepts. No JS equivalent exists after 4 subconscious runs and 23+ days. The hook pattern is established — adding Check 9 is mechanical.

## Implementation Sketch

1. **Fix AdminAnalyticsPage.jsx:117-122** — replace 6 `.catch(() => null)` with the established pattern from the marketing page fix:
   ```js
   apiFetch("/overview").catch((err) => {
     console.warn("AdminAnalytics: overview fetch failed:", err);
     return null;
   }),
   ```
   Apply to all 6 calls (overview, weekly-growth, monthly-growth, plan-distribution, revenue-trends, industry-breakdown).

2. **Add Check 9 to `scripts/hooks/pre-commit`** after the existing Python checks:
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

3. **Test the guard** — add synthetic `.catch(() => null)` to a staged JS file, run `bash scripts/hooks/pre-commit`, confirm BLOCKED. Revert.

4. **Update CLAUDE.md Automation section** — add "Check 9: JS silent catch guard" to the pre-commit bullet.

5. **Verify** — `bash scripts/hooks/pre-commit` passes on clean HEAD after fix.

## What This Replaces
Completes run 3 recommendation from 2026-04-11 (23+ days). The manual violation fix in `e68677a` was the ad-hoc patch; this pre-commit guard is the systematic completion.

## Confidence
**HIGH** — Quadruple evidence: (1) original violations fixed, confirming the manual-fix-without-guard cycle, (2) AdminAnalyticsPage.jsx has 6 new violations confirming pattern recurrence, (3) pre-commit has no JS equivalent of Check 3, (4) 21-issue sprint starting today. Moratorium mandate explicit. S-effort.

## Governance Correction
Original violation sites (MarketingDashboardPage.jsx + LocalSEOPage.jsx) FIXED by `e68677a`. New cluster at AdminAnalyticsPage.jsx:117-122. Pre-commit guard (Check 9) never added. Run 3 status: still `pending_approval` for the guard.

## Moratorium Status Note
After implementation: 4→3 pending winners → moratorium lifts. Run 7 (Widget Sync Guard) next priority.
