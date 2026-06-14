# Winning Concept — 2026-05-01 (Run 12)

## Recommendation
Fix AdminAnalyticsPage.jsx:117-122 (add `console.warn` to 6 silent catches), then add JS Silent Catch as **Check 10** in `scripts/hooks/pre-commit` — completing the run 3 recommendation with corrected check numbering and Onboarding V2 sprint urgency.

## Why This, Why Now

**Check number corrected.** All prior winning concepts (runs 9–11) described this as "Check 9." Direct inspection of `scripts/hooks/pre-commit` shows 9 existing checks (Check 9 = "dropped conversations.messages queries"). The JS silent catch guard is Check 10. This error has persisted through 3 recommendation cycles and may be causing implementation friction.

**Pattern recurs without a guard.** `e68677a` (2026-04-28) manually fixed 4 violations (widget_chat.py, AuthContext, MarketingDashboard, LocalSEO). Yet AdminAnalyticsPage.jsx:117-122 already had 6 `.catch(() => null)` calls unaddressed. Issue #109 (nightly review 2026-05-01) formally tracks the AdminAnalyticsPage cluster. The fix-without-guard cycle is now 4 iterations — the only sustainable path is the guard.

**Onboarding V2 sprint starts now.** `plans/onboarding-v2_plan.md` (21 issues, `37c151c`) generates JSX files this sprint. Every new component is a risk vector for silent catches if the guard is absent. Installing the guard before the first commit is the cheapest moment.

**Em-dash blocker for run 8 confirmed still present.** Nightly review incorrectly reported em-dash as cleared. Direct `check_project_invariants.py` run shows 9 violations (WizardStepAutoKB + AutomationActivityCard). This means JS Silent Catch remains the only unblocked S-effort pre-commit improvement available.

## Implementation Sketch

1. **Fix AdminAnalyticsPage.jsx:117-122** — replace 6 `.catch(() => null)` with the established pattern:
   ```js
   apiFetch("/overview").catch((err) => {
     console.warn("AdminAnalytics: overview fetch failed:", err);
     return null;
   }),
   apiFetch("/weekly-growth").catch((err) => {
     console.warn("AdminAnalytics: weekly-growth fetch failed:", err);
     return null;
   }),
   apiFetch(`/monthly-growth?months=${months}`).catch((err) => {
     console.warn("AdminAnalytics: monthly-growth fetch failed:", err);
     return null;
   }),
   apiFetch("/plan-distribution").catch((err) => {
     console.warn("AdminAnalytics: plan-distribution fetch failed:", err);
     return null;
   }),
   apiFetch(`/revenue-trends?months=${months}`).catch((err) => {
     console.warn("AdminAnalytics: revenue-trends fetch failed:", err);
     return null;
   }),
   apiFetch("/industry-breakdown").catch((err) => {
     console.warn("AdminAnalytics: industry-breakdown fetch failed:", err);
     return null;
   }),
   ```

2. **Add Check 10 to `scripts/hooks/pre-commit`** after the existing Check 9 block:
   ```bash
   # Check 10: JS silent catch — .catch(() => null) / .catch(() => {})
   printf "Check 10: JS silent catch guard... "
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

3. **Test the guard** — add `.catch(() => null)` to a staged JS file; run `bash scripts/hooks/pre-commit`; confirm BLOCKED; revert.

4. **Update CLAUDE.md Automation section** — correct "Check 9" → "Check 10: JS silent catch guard" in the pre-commit bullet.

5. **Close Issue #109** via commit message: `fix(admin-analytics): add console.warn to 6 silent catches, closes #109`.

6. **Verify** — `bash scripts/hooks/pre-commit` passes on clean HEAD after fix.

## Side Note: Run 8 Prerequisite (Em-dash Scope Fix)

Before run 8 (Wire check_project_invariants.py) can be implemented, the em-dash check must be scoped to exclude JSX files. The fix is one line in `check_project_invariants.py`:
```python
# In the em-dash check, skip .jsx and .tsx files
if path.endswith(('.jsx', '.tsx')):
    continue
```
This is NOT part of this recommendation. Flag to human: run 8 has a two-step prerequisite, not just wiring.

## What This Replaces
Completes run 3 recommendation from 2026-04-11 (24 days). Corrects the check numbering error that has persisted since run 9. The moratorium-mandated repetition stops here.

## Confidence
**HIGH** — Evidence: (1) AdminAnalyticsPage 6 violations confirmed live; (2) Issue #109 open externally; (3) pre-commit check number corrected via direct inspection; (4) Onboarding V2 sprint starting; (5) em-dash blocker for run 8 confirmed still active (scoping fix needed first). All blockers on run 3 path are zero.

## Moratorium Status Note
Implementation of this recommendation: 4 pending → 3 pending → moratorium lifts.
Moratorium lift enables: golden eval harness CI wiring (run 13 candidate, parking lot ROI 2.5).
Run 8 next after moratorium lifts, but requires em-dash scope fix as prerequisite step.
