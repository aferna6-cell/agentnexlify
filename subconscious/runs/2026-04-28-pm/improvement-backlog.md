# Improvement Backlog — 2026-04-28-pm

## Active
- **JS Silent Catch Pre-commit Guard (Check 9)** — Add ~8 lines to `scripts/hooks/pre-commit` blocking `.catch(() => null/{})`  in staged JS/JSX/TS/TSX. Fully closes run 3. Lifts moratorium on implementation. See `winning-concept.md`.

## Moratorium Status
**LIFTING** — e68677a (2026-04-28) classified as `implemented_weakened` for run 3. Pending count after governance update: 4 (runs 3-weakened, 4, 7, 8).
After implementing this run's winner (Check 9): run 3 → `implemented`. Pending: 3 (runs 4, 7, 8) → **moratorium lifted**.

| Winner | Run | Days Pending | Status |
|--------|-----|-------------|--------|
| ~~Add Lead Source Analytics Chart~~ | 2 | — | **IMPLEMENTED** |
| JS + Python Silent Catch Guard | 3 | 17 | **implemented_weakened** → winner closes this fully |
| AI-to-Human Handoff (Explicit Trigger v1) | 4 | 12+ | pending_approval |
| Widget 3-Copy Sync Guard | 7 | 4 | pending_approval |
| Wire check_project_invariants.py | 8 | 3 | pending_approval |

## Parking Lot (survived debate, not chosen this run)

- **Wire check_project_invariants.py into pre-commit** [ROI 2.2, Run 8] — S-effort. `scripts/check_project_invariants.py` stdlib-only, unwired. Add call after existing Python checks in pre-commit. Next-in-line after run 3 closes.

- **Widget 3-Copy Sync Guard** [ROI 2.3, Run 7] — S-effort. Create `scripts/check-widget-sync.sh` + wire into pre-push. landing-page-v2/ is do-not-touch; primary guard is widget/ → frontend/public/widget/ 2-way check.

- **AI-to-Human Handoff (Explicit Trigger v1)** [ROI 3.0, Run 4] — 1.5-2 day build. Highest ROI in backlog. Critical for all 7 verticals. Infrastructure exists (conversations table, webhooks, Twilio, Resend). Unlock when moratorium lifts.

- **Stripe Webhook Smoke Tests** [ROI 2.2, new this run] — stripe_webhooks.py 188 LOC, no test files. Issue #99 class (SignatureVerificationError catch order → 500 not 400) would be caught. Create `backend/tests/test_stripe_webhooks_smoke.py` with 4-5 tests.

- **local_seo_handlers.py god class split** [ROI 1.9, new this run] — 886 LOC, >600 threshold. Split into backend/services/local_seo/ package: audit_handlers.py, keyword_handlers.py, competitor_handlers.py, geo_handlers.py. Mirrors run 5 widget_helpers split pattern. L-effort.

- **widget_helpers Split Smoke Tests** [ROI 2.0] — Run 5 (6cf4646) still `implemented_unverified`. Smoke test 3 split modules.

- **Bug-patterns.md Split by Month** [ROI 1.8] — 2,200+ lines. Auto-logger writes to it. Split into monthly files + INDEX.md.

- **_find_tenant_by_phone O(N) Scan** [ROI 1.7] — twilio_webhooks.py:69 loads all tenants. Add DB index or LRU cache.

- **Widget Hot-Zone Regression Suite** [ROI 2.1] — Playwright confirmation needed. `npx playwright install` first.

- **Managed Agents Integration Tests** [ROI 1.5] — Expand test_managed_agents.py to cover all 5 HTTP endpoints.

## Rejected This Run
- None outright killed. Ideas 2 and 3 WEAKENED on moratorium ordering grounds; both remain valid and pending.

## Questions for Next Run
1. Was Check 9 (JS silent catch guard) implemented? If yes, run 3 → `implemented`, pending = 3, moratorium lifted — generate fresh ideas not from the active_directions queue.
2. Was check_project_invariants.py wired into pre-commit (run 8)? If yes, pending = 2 (runs 4, 7).
3. Does local_seo_handlers.py continue to grow? At 886 LOC today; if it hits 1000+ by next run, elevate the split to higher priority.
4. Are issue #93 (fraud guard coupon bug) and issue #99 (Stripe sig catch order) closed? If #99 still open >3 days, consider elevating Stripe smoke tests to winner.
