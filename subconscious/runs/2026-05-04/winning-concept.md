# Winning Concept — 2026-05-04 (Run 13)

## Recommendation
Implement the JS Silent Catch Guard: fix AdminAnalyticsPage.jsx:117-122 (add `console.warn` to 6 silent catches), then add Check 10 to `scripts/hooks/pre-commit` — completing run 3's 24-day-old recommendation and lifting the moratorium.

## Why This, Why Now

**Moratorium mandate, day 24+.** This recommendation has survived 10 consecutive debate cycles (runs 3, 9, 10, 11, 12). Governance.json moratorium_active=true explicitly requires re-recommending until implementation occurs. No new blockers exist. The check numbering error (Check 9 vs Check 10) was corrected in run 12.

**Violations confirmed live.** Direct grep of AdminAnalyticsPage.jsx on 2026-05-04 shows 6 `.catch(() => null)` at lines 117-122 — unchanged since Issue #109 was opened. The pattern recurred in AdminAnalyticsPage without a guard, exactly as predicted in run 9's evidence (e68677a fixed 4 violations; unguarded codebase re-acquired 6 more within 3 days).

**Onboarding V2 sprint is active.** plans/onboarding-v2_plan.md (21 issues) is in sprint. New JSX components are being written. Every new JSX component is a risk vector for silent catches if Check 10 is absent. Installing the guard before the first Onboarding V2 commit is the cheapest possible moment.

**S-effort, copy-paste-ready.** Run 12's winning-concept.md contains the exact regex, exact bash block, exact console.warn replacements. No design work required. Estimated implementation time: 30 minutes.

## Implementation Sketch

### Step 1: Fix AdminAnalyticsPage.jsx:117-122
Replace 6 `.catch(() => null)` with the established console.warn pattern:

```js
// Before (line 117-122):
apiFetch("/overview").catch(() => null),
apiFetch("/weekly-growth").catch(() => null),
apiFetch(`/monthly-growth?months=${months}`).catch(() => null),
apiFetch("/plan-distribution").catch(() => null),
apiFetch(`/revenue-trends?months=${months}`).catch(() => null),
apiFetch("/industry-breakdown").catch(() => null),

// After:
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

### Step 2: Add Check 10 to scripts/hooks/pre-commit
Insert after the existing Check 9 block (after line ~232):

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

### Step 3: Test the guard
```bash
# Stage a file with a silent catch and confirm BLOCKED
echo 'fetch("/api").catch(() => null)' >> /tmp/test-silent.js
git add /tmp/test-silent.js 2>/dev/null || true
# Actually: create temp staged content in a watched file, run hook, confirm block
bash scripts/hooks/pre-commit
# Then revert test content
```

### Step 4: Close Issue #109
Commit message: `fix(admin-analytics): add console.warn to 6 silent catches, closes #109`

### Step 5: Verify clean HEAD
```bash
bash scripts/hooks/pre-commit
```
All 10 checks should pass (no silent catches in staged files on clean HEAD).

---

## Bonus Step: Unblock Run 8 (Em-dash Scope Fix)
This is NOT required for the above but adds zero risk and unblocks a 10-day-old pending winner:

In `scripts/check_project_invariants.py`, in the em-dash check loop:
```python
# Skip JSX/TSX files — em-dash is a valid UI display char (e.g. || '—' for empty table cells)
if path.endswith(('.jsx', '.tsx')):
    continue
```

After this one-line change, rerun `python3 scripts/check_project_invariants.py` — should show 0 em-dash violations. Run 8 ("Wire check_project_invariants.py into pre-commit") then has no blockers.

---

## What This Replaces
Completes run 3 recommendation from 2026-04-11 (now 24 days). Moratorium-mode recommendations (runs 9–13) all pointed here. Moratorium lifts after implementation: pending 4 → 3.

## Moratorium Cascade on Lift
Once this is implemented:
- pending_approvals: 4 → 3 (moratorium lifts)
- Run 14 winner candidate: **Wire golden eval harness to CI** (parking lot ROI 2.5, Issue #110, explicitly flagged as "first post-moratorium winner")
- Run 8 becomes implementable after em-dash scope fix (above bonus step)

## Confidence
**HIGH** — Evidence: (1) AdminAnalyticsPage 6 violations confirmed live 2026-05-04; (2) Issue #109 open externally; (3) pre-commit Check 10 confirmed absent; (4) Onboarding V2 sprint active; (5) 10 consecutive run recommendations; (6) zero implementation blockers; (7) implementation sketch copy-paste-ready from run 12.
