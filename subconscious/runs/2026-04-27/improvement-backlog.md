# Improvement Backlog — 2026-04-27

## Active
- **JS + Python Silent Catch Guard** — Add Check 9 to `scripts/hooks/pre-commit` (JS `.catch(() => null/{})`). Patch `widget_chat.py:295` bare except with `logger.warning(...)`. Fix 3 known JS violations before committing. S-effort. Lifts moratorium when implemented + 1 other. See `winning-concept.md`.

## Moratorium Status
**ACTIVE** — 4 pending_approval items after governance correction (run 2 marked implemented).

| Winner | Run | Days Pending | Status |
|--------|-----|-------------|--------|
| ~~Add Lead Source Analytics Chart~~ | 2 | — | **IMPLEMENTED** (AnalyticsPage.jsx — governance correction this run) |
| JS + Python Silent Catch Guard | 3 | 16+ | **pending_approval ← ACTIVE WINNER** |
| AI-to-Human Handoff (Explicit Trigger v1) | 4 | 11+ | pending_approval |
| Widget 3-Copy Sync Guard | 7 | 3+ | pending_approval |
| Wire check_project_invariants.py | 8 | 2+ | pending_approval |

Lift condition: implement run 3 winner → 3 remaining → moratorium lifted.

## Parking Lot (survived debate, not chosen)

- **Widget 3-Copy Sync Guard** [ROI 2.3, Run 7] — Create `scripts/check-widget-sync.sh` + pre-push wire. S-effort. Second-oldest pending after JS catch guard.

- **Wire check_project_invariants.py into pre-commit** [ROI 2.2, Run 8] — `scripts/check_project_invariants.py` exists. Add call in `scripts/hooks/pre-commit` after existing Python checks. S-effort.

- **AI-to-Human Handoff (Explicit Trigger v1)** [ROI 3.0, Run 4] — 1.5-2 day build. Infrastructure exists. Critical gap all 7 industries. Highest ROI in backlog.

- **Fix Billing Bugs #93+#94** [URGENT, not moratorium item] — `fraud_guard.py:121-123`: skip when `payment_status == "no_payment_required"`. Lines 135-147: guard `charges_data` indexing. HIGH severity active today. Fix via GitHub issues #93/#94, not via subconscious cycle.

- **Fix Stripe SignatureVerificationError catch (Issue #99)** [ROI 1.8] — Split `except (stripe.SignatureVerificationError, Exception)` into ordered clauses in `stripe_webhooks.py:46`. Correct 500 → 400 on bad sig.

- **widget_helpers Split Smoke Tests** [ROI 2.0] — Write `backend/tests/test_widget_helpers_smoke.py`: import each of 3 split modules + call one function. Verify run 5 is clean.

- **Widget Hot-Zone Regression Suite** [ROI 2.1] — Playwright confirmation still needed. `npx playwright install` then promote.

- **Bug-patterns.md Split by Month** [ROI 1.8] — 2,200+ lines and growing. Split into monthly files + INDEX.md. Update auto-logger path.

- **Stripe Billing Smoke Tests** [ROI 2.2] — 821f660 touched 16 billing files, zero QA. Frame as plan-tier contract tests.

- **_find_tenant_by_phone O(N) Scan (Issue #98)** [ROI 1.7] — `twilio_webhooks.py:69` loads all tenants for phone normalization. Add DB index or in-process LRU cache with TTL.

- **Managed Agents Integration Tests** [ROI 1.5] — Expand `backend/tests/test_managed_agents.py` to cover all 5 HTTP endpoints.

## Rejected This Run
- None killed outright. Ideas 2 and 3 WEAKENED on moratorium protocol grounds, moved to parking lot.

## Questions for Next Run
1. Is issue #93 (coupon users paused by fraud guard) fixed? If open >3 days, escalate to subconscious winner.
2. Was JS + Python Silent Catch Guard implemented? If yes, moratorium lifts — generate fresh ideas.
3. Are any of the 4 pending items marked `implemented` since this run? Recount pending to determine if moratorium lifted.
