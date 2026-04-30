# Improvement Backlog — 2026-04-30-pm (Run 11)

## Active (Moratorium — implement in order)

1. **JS Silent Catch Pre-commit Guard** (Run 3, 2026-04-11, day 23+) — WINNER this run.
   Fix AdminAnalyticsPage.jsx:117-122 + add Check 9 to pre-commit. S-effort. Implements → 4→3 pending → moratorium lifts.

2. **Widget 3-Copy Sync Guard** (Run 7, 2026-04-24) — Next after moratorium lifts.
   Fix CLAUDE.md Invariant #4 + create scripts/check-widget-sync.sh + wire into pre-push. S-effort.

3. **Wire check_project_invariants.py** (Run 8, 2026-04-25) — After run 7.
   Diagnose em-dash crash in WizardStepAutoKB.jsx first. Then wire into pre-commit. S-effort.

4. **AI-to-Human Handoff v1** (Run 4, 2026-04-16) — After moratorium fully lifted.
   Explicit-trigger-only. 1.5-2 days. All 7 industries.

## Parking Lot (survived debate this run)

- **Wire golden eval harness to weekly CI** (NEW, run 11) — ROI 2.5. `backend/tests/evals/` ready. Add `.github/workflows/lead-qualifier-eval.yml` Monday cron. Requires `LEAD_QUALIFIER_AGENT_ID` secret. PROMOTE AS RUN 12 WINNER once moratorium lifts.
- **Onboarding V2 characterization tests** (NEW, run 11) — ROI 1.7. Write before first sprint issue begins. Prevents `implemented_unverified` syndrome.
- **Fix em-dash + wire check_project_invariants.py** — (listed as active item 3)
- **widget_helpers Split Smoke Tests** — ROI 2.0. `backend/tests/test_widget_helpers_smoke.py`.
- **Widget Hot-Zone Regression Suite** — ROI 2.1. Blocked on Playwright confirmation.
- **Stripe Billing Smoke Tests** — ROI 2.2. 821f660 touched 16 billing files.
- **Bug patterns monthly split** — ROI 1.8. 2,320 lines → monthly files + INDEX.md.
- **Managed Agents Automated Integration Tests** — ROI 1.5.
- **Small Business SaaS KB Category Seed** — ROI 1.5.

## Rejected This Run
None killed in debate. All 3 debated survived (1 winner, 2 parking lot).

## Governance Correction Applied
- Run 3 evidence updated: original violations (MarketingDashboardPage.jsx + LocalSEOPage.jsx) FIXED by `e68677a`. New evidence: AdminAnalyticsPage.jsx:117-122 (6 instances). Pre-commit Check 9 never added.

## Questions for Next Run
1. Have AdminAnalyticsPage.jsx violations been fixed and pre-commit Check 9 added? (moratorium lift)
2. Is `LEAD_QUALIFIER_AGENT_ID` available in GH Secrets?
3. What exactly causes check_project_invariants.py to fail on WizardStepAutoKB.jsx?
4. Has any onboarding-v2 issue started without characterization tests?
