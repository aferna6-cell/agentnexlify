# Winning Concept — 2026-06-12-pm (Run 57)

## Recommendation
Add a `from __future__ import annotations` violation check to `.github/workflows/pr-check.yml`
— FAIL on any match in `backend/**/*.py` — enforcing the guard at CI level where it cannot be
bypassed.

## Why This, Why Now

Pre-commit Check 2 (FAIL-mode, added run 56) only scans `$STAGED_FILES` matching `*routers*.py`
and runs ONLY on local developer machines. All commits landing via GitHub PR squash merges,
Claude agent loop commits, or nightly autonomous commits bypass the hook entirely. This was proven
today: push_subscriptions.py (in routers/) landed with the violation despite Check 2 existing, and
activation_nudges.py (in services/) was never covered at all. The result: 4 infected files grew to
8 in 24 hours (PRs #232 → #238 → #254). CI enforcement runs on every PR regardless of commit
source — no bypass path. The nightly successfully created lead-qualifier-eval.yml (run 47 winner)
via the same AUTONOMOUS-EXECUTABLE mechanism. This is a one-step extension of proven capability.

## Implementation Sketch

1. Read `.github/workflows/pr-check.yml` to find the correct job and step insertion point.
2. Add a new step (after existing quality checks, before deploy):
   ```yaml
   - name: Check for from __future__ import annotations in FastAPI files
     run: |
       if grep -rl "from __future__ import annotations" backend/ --include="*.py"; then
         echo "ERROR: from __future__ import annotations found in backend Python files."
         echo "This breaks FastAPI request parsing (Pydantic type resolution fails at runtime)."
         echo "Remove the import. See CLAUDE.md Critical Invariant #5."
         exit 1
       fi
       echo "OK: no from __future__ import annotations violations."
   ```
3. Commit as `ci: add from __future__ guard to PR check (CLAUDE.md Invariant #5)`.
4. The step will immediately flag all 8 current violations on the next PR — this is expected
   and intentional. Human must then fix the 8 files (5 min, line-1 deletion per file).

## Bonus Actions (execute alongside winner)

**Bonus A — Fix 8 JSX em-dash violations (AUTONOMOUS-EXECUTABLE, ~2 min):**
Replace em-dash chars with hyphens in:
- `frontend/src/components/CookieConsent.jsx:31`
- `frontend/src/components/MarketingUpsell.jsx:3`
- `frontend/src/components/App.jsx:329`
- `frontend/src/components/Sidebar.test.jsx:27`
- `frontend/src/components/Sidebar.test.jsx:49`
- `frontend/src/components/Sidebar.jsx:386`
- `frontend/src/components/DemoBanner.jsx:4`
- `frontend/src/components/DemoBanner.jsx:7`
Clears the em-dash invariant failure (one of 3 exits-1 causes).

**Bonus B — Remove `from __future__` from 8 backend files (HUMAN-REQUIRED, ~5 min):**
Delete line 1 from:
- `backend/routers/auth_billing.py`
- `backend/routers/auth_google.py`
- `backend/routers/auth_password_reset.py`
- `backend/routers/channels_instagram.py`
- `backend/routers/embed_instructions.py`
- `backend/routers/push_subscriptions.py`
- `backend/services/activation_nudges.py`
- `backend/services/branding_helpers.py`
Together with Bonus A, clears all invariant failures → check_project_invariants exits 0 →
Item A (Check 10) auto-wires in next nightly cycle.

## What This Replaces

Run 56 winner (Check 13: pre-commit `from __future__` guard) remains valid as a local-dev
complement. This CI check is the CI-layer enforcement that Run 56 assumed was already provided
by Check 2 — it wasn't. Both should exist: Check 2 (pre-commit, local) + this CI step (server,
all paths). This run's winner adds the missing server-side layer.

## Confidence
HIGH — root cause confirmed by direct code inspection (Check 2 reads `$STAGED_FILES`, misses
GitHub merge commits; pattern `*routers*.py` misses services/). Mechanism proven by run 47
(nightly autonomous CI YAML creation via lead-qualifier-eval.yml). Zero false positive risk in
current codebase.
