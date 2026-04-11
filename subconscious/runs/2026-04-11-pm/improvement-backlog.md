# Improvement Backlog — 2026-04-11-pm

## Active
- **JS Silent Catch Pre-commit Guard** — Add Check 8 to `scripts/hooks/pre-commit` to emit WARNING on `.catch(() => null/{})` patterns in staged JS/TS files. Atomic, zero-infra, compounds. See `winning-concept.md`.

## Parking Lot (survived debate but not chosen)

- **Widget Click Regression Guard (Playwright E2E)** [ROI 2.0] — Parking lot carry-over. Still valid: widget gained complexity (migration 101, widget_chat.py 198 lines). BLOCKER: verify Playwright browser binaries are installed (`npx playwright install --check`) before writing tests. Once infra confirmed, pick for next code_health run.

- **Onboarding AI Parser Edge Case Tests** [ROI 1.5] — Parking lot carry-over. `planning/specs/lead-parser-replacement_spec.md` now exists (committed 177251d today), making this even more timely. Write tests against parser seam before replacement. Ready when lead parser replacement work begins.

- **Ingest 5 Competitor Briefs into KB** [Low Effort] — Valid. `b97928a` added 5 briefs (GoHighLevel, Drillbit, Birdeye, Oscar Chat, Phonely). First: locate brief files (`grep -r "GoHighLevel" docs/`), assess quality, then `/kb-ingest` × 5. KB "Competitors" category currently has 1 article — this would create a proper competitive intelligence layer.

- **Managed Agents Automated Integration Tests** [Medium Effort] — Valid. Daily log Apr 10 Priority 1: "QA Managed Agents." 5 agents active. Smoke scripts are manual. Expand `backend/tests/test_managed_agents.py` to cover all 5 HTTP endpoints with mocked Claude API.

## Rejected This Run
_(None killed outright — all top-3 survived or weakened into parking lot.)_

## Questions for Next Run
1. Is Playwright installed in CI? (`npx playwright install --check` or `which chromium`) — determines if Widget Regression Guard can execute.
2. Have the 2 pending-approval recommendations (run 1: stale skills, run 2: lead source analytics) been implemented? If neither has shipped, should the system escalate or diversify further?
3. Are the 5 competitor briefs from commit `b97928a` in a single directory? Locate before proposing KB ingestion.
