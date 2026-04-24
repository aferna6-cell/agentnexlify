# Improvement Backlog — 2026-04-24

## Active
- **Widget 3-Copy Sync Guard** — Fix CLAUDE.md Invariant #4 to list all 3 widget paths. Create
  `scripts/check-widget-sync.sh`. Wire into pre-push hook. S-effort, zero dependencies. See
  `winning-concept.md`.

## Implementation Lag Alert (escalate to human)
Prior winners accumulating without implementation. Actual status as of run 7:

| Winner | Run | Status |
|--------|-----|--------|
| Update 4 stale skills per weekly discovery | 1 | status unknown |
| Add Lead Source Analytics Chart | 2 | unimplemented |
| JS Silent Catch Pre-commit Guard | 3 | **unimplemented (13+ days)** |
| AI-to-Human Handoff (Explicit Trigger v1) | 4 | unimplemented |
| widget_helpers.py split | 5 | implemented (6cf4646) |
| Migration Duplicate Number Pre-commit Guard | 6 | partially implemented (Check 5 WARNING, not FAIL) |

→ Human should review. If implementation continues to lag, subconscious should declare a
moratorium on new recommendations until backlog clears.

## Parking Lot

- **Widget Hot-Zone Regression Suite** [ROI 2.1] — WEAKENED this run. Pre-condition met (split
  done 6cf4646). Still blocked on Playwright confirmation: `npx playwright install --check`.
  Promote to winner candidate in run 8 if confirmed.

- **Stripe Billing Smoke Tests / Plan-Tier Contract Tests** [ROI 2.2] — WEAKENED this run.
  Correct diagnosis (821f660 touched 16 billing files, zero tests). Frame as billing constants
  harness + plan-tier contract tests. Revisit next pricing sprint.

- **JS Silent Catch Pre-commit Guard** [ROI 2.4] — Run 3 winner, unimplemented 13+ days. Add as
  Check 9 to `scripts/hooks/pre-commit`. 3 known violations: `MarketingDashboardPage.jsx:96`,
  `LocalSEOPage.jsx:262`, `AuthContext.jsx:89`.

- **AI-to-Human Handoff (Explicit Trigger v1)** [ROI 3.0] — Run 4 winner, unimplemented. 1.5-2
  day build. Infrastructure exists. Critical gap all 7 industries.

- **Add Lead Source Analytics Chart** [ROI 2.67] — Run 2 winner, unimplemented. source column
  exists, Recharts installed. Low effort.

- **Bug-patterns.md Split by Month** [ROI 1.8] — 2,204 lines, growing daily. Split into monthly
  files + INDEX.md. Update auto-logger path.

- **Widget Click Regression Guard (Playwright)** [ROI 2.0] — Confirm `npx playwright install
  --check` first.

- **Onboarding AI Parser Edge Case Tests** [ROI 1.5] — spec exists.

- **Managed Agents Automated Integration Tests** [ROI 1.5] — 5 endpoints untested.

- **Migration Safety Net Pre-Push Check** [ROI 1.8] — Add after apply-migration helper exists.

- **Small Business SaaS KB Category Seed** [ROI 1.5] — `/kb-discover` on 3 SMB queries.

- **Ingest 5 Competitor Briefs into KB** [Low Effort] — research-briefs/ exists, `/kb-ingest x5`.

## Rejected This Run
_(No ideas killed outright — top 3 all survived or weakened into parking lot.)_

## Questions for Next Run
1. Is Playwright installed? `npx playwright install --check` — open since run 2.
2. Has JS Silent Catch guard (run 3) been implemented? If not by run 8, escalate directly.
3. Has the compromised admin API key in Railway been rotated? P0, day 19.
4. Are all 3 widget copies currently in sync? `bash scripts/check-widget-sync.sh` will answer
   this at verification time (once created).
