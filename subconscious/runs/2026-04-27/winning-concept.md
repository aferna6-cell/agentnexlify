# Winning Concept — 2026-04-27

## Recommendation
Implement the JS Silent Catch Pre-commit Guard (Run 3 winner, 16+ days pending) AND patch the Python equivalent in `widget_chat.py:295` — together these close both the JS and Python silent-swallow-exception pattern in one S-effort PR.

## Why This, Why Now
Run 3 winner "JS Silent Catch Pre-commit Guard" has been pending since 2026-04-11 (16 days). Moratorium protocol mandates recommending the oldest pending winner. Issue #97 from today's nightly review adds fresh urgency: `widget_chat.py:295` has a bare `except Exception: plan = "free"` with zero logging — paid tenants are silently rate-limited at free tier (30 rpm instead of their plan tier) whenever a DB lookup fails, with no log to detect it. This extends the original JS-only recommendation to cover the same pattern in Python. Three JS violations confirmed active (MarketingDashboardPage.jsx:96, LocalSEOPage.jsx:262, AuthContext.jsx:89). Both fixes are S-effort: 3 lines in the pre-commit hook + 1 log line in widget_chat.py.

## Implementation Sketch
1. **Patch widget_chat.py:295** — in the `except Exception:` block add:
   ```python
   except Exception as exc:
       logger.warning("_chat_rate_limit fallback to free tier for key=%s: %s", key, exc)
       plan = "free"
   ```
2. **Add Check 9 to `scripts/hooks/pre-commit`** after existing checks (~line 155):
   ```bash
   # Check 9: JS silent catches (.catch(() => null) or .catch(() => {}))
   JS_SILENT=$(git diff --cached --name-only | grep '\.jsx\?\|\.tsx\?' | xargs grep -lE '\.catch\(\(\)\s*=>\s*(null|\{\})' 2>/dev/null || true)
   if [ -n "$JS_SILENT" ]; then
     echo "BLOCKED: silent JS catch detected in: $JS_SILENT"
     echo "Replace .catch(() => null) with a real error handler or at minimum a console.error."
     exit 1
   fi
   ```
3. **Fix known violations first** (or they'll block your own commit):
   - `MarketingDashboardPage.jsx:96` — add real error handler
   - `LocalSEOPage.jsx:262` — add real error handler
   - `AuthContext.jsx:89` — add real error handler
4. **Test the hook** — create a test file with `.catch(() => null)`, stage it, run `bash scripts/hooks/pre-commit`, confirm BLOCKED.
5. **Verify** — `bash scripts/hooks/pre-commit` passes clean on HEAD.
6. **Governance update** — mark Run 3 as `implemented`. Recalculate moratorium: 3 pending (runs 4, 7, 8) → moratorium lifted.

## Governance Correction (apply this run)
Lead Source Analytics (Run 2, 2026-04-06) is already implemented in `frontend/src/pages/AnalyticsPage.jsx` (fetchLeadSources + BarChart, confirmed). Governance must be updated: `status: "implemented"` for run 2 entry. This corrects pending count from 5 → 4 before this run's recommendation.

## What This Replaces
Run 3 winner "JS Silent Catch Pre-commit Guard" (active_directions entry from 2026-04-11). Extended to cover Python bare-catch-no-log pattern per new evidence.

## Confidence
**HIGH** — Triple-backed: (1) run 3 winner is moratorium's oldest pending; (2) issue #97 provides fresh Python instance with active revenue impact; (3) pre-commit guard is established pattern (6 existing checks). Debate: Idea 1 SURVIVED all 3 challenges, Ideas 2 and 3 WEAKENED on moratorium protocol grounds.

## Urgency Note (not subconscious winner — fix via normal sprint)
Issue #93 HIGH billing bug (`fraud_guard.py:121-123` pauses coupon/trial signups) is active and revenue-impacting. Fix independently via GitHub issue #93 — do not wait for subconscious cycle. 2-line fix: `if payment_status == "no_payment_required": return None`.
