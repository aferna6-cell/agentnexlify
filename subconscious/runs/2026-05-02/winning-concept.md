# Winning Concept — 2026-05-02 (Run 13)

## Recommendation
Fix AdminAnalyticsPage.jsx:117-122 (add `console.warn` to 6 silent catches, closes Issue #109), then add JS Silent Catch as **Check 10** in `scripts/hooks/pre-commit` — same recommendation as run 12, moratorium mandate, day 21 of oldest pending winner.

## Why This, Why Now

**Still confirmed, still unimplemented.** Direct grep this run: AdminAnalyticsPage.jsx:117-122 has 6 `.catch(() => null)` unchanged since Issue #109 opened (nightly 2026-05-01). Pre-commit still has exactly 9 checks (verified `echo -n` count). The implementation sketch from run 12 is complete with correct check numbering. No new blockers have appeared.

**Onboarding V2 sprint is live.** `plans/onboarding-v2_plan.md` (21 issues) entered active sprint on 2026-05-01. Every new JSX component generated this sprint is a potential silent-catch vector. Installing Check 10 before the first sprint commit is the cheapest insurance available — after commits land, the guard only catches future violations, not ones already committed.

**New evidence confirms pattern recurs in new code.** `email_sequences.py` (shipped `fa466ca`, 2026-05-01) was reviewed and has no silent catches — but nightly review 2026-05-02 opened Issues #112 (N+1) and #113 (duplication) on that same file. The pattern observation: N+1 and code duplication are the quality issues that slip in on new features; silent catches are the quality issue that slips in on dashboard pages. Without Check 10, every new dashboard page in the Onboarding V2 sprint carries this risk.

**Moratorium math unchanged.** 4 pending approvals. Implementing this drops to 3, lifts the moratorium. First post-moratorium winner is golden eval harness CI (parking lot ROI 2.5, Issue #110) — concrete downstream value waiting.

## Implementation Sketch

1. **Fix AdminAnalyticsPage.jsx:117-122** — replace 6 `.catch(() => null)` with established pattern:
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

2. **Add Check 10 to `scripts/hooks/pre-commit`** after existing Check 9 block (around line 232):
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

3. **Test the guard locally:**
   ```bash
   # Add a silent catch to any staged JS file, then:
   bash scripts/hooks/pre-commit  # expect BLOCKED
   # Revert the test change
   ```

4. **Close Issue #109** — include in commit message: `fix(admin-analytics): add console.warn to 6 silent catches, closes #109`

5. **Verify pre-commit passes clean on HEAD** — `bash scripts/hooks/pre-commit`

## Downstream: Run 8 Prerequisite Note
Before run 8 can be implemented (`Wire check_project_invariants.py`), the em-dash check must skip `.jsx/.tsx` files:
```python
# In check_project_invariants.py em-dash check loop:
if path.suffix in ('.jsx', '.tsx'):
    continue
```
This is NOT part of this recommendation — it's a blocker note on run 8.

## Escape Hatches for Other Silent Catches
`SignupPage.jsx:122/141/165`, `ConversationsPage.jsx:207-208`, `DocumentsPage.jsx:175` all have `.catch(() => ({}))`/`.catch(() => [])` — these are graceful JSON parse fallbacks, not API-call swallowing. They could use `// ok-silent-catch` annotation to pass Check 10 without changing behavior.

## What This Replaces
Completes run 3 recommendation (2026-04-11, 21 days). Corrects check numbering error that persisted through runs 9–12. Lifts moratorium after 5 consecutive moratorium-mode runs.

## Confidence
**HIGH** — Evidence: (1) AdminAnalyticsPage 6 violations confirmed live this run; (2) Issue #109 open; (3) Pre-commit check count verified = 9; (4) Onboarding V2 sprint live; (5) No blockers on run 3 path; (6) Implementation sketch complete with correct numbering from run 12.

## Moratorium Status
- **Before implementation:** 4 pending approvals (runs 3, 4, 7, 8)
- **After implementation:** 3 pending approvals → moratorium lifts
- **Run 14 candidate:** Wire golden eval harness to CI (parking lot ROI 2.5, Issue #110)
- **Run 14+1 candidate:** em-dash scope fix + wire check_project_invariants.py (run 8 unblocked)
