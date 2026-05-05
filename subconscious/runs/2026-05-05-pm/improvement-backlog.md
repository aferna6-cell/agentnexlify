# Improvement Backlog — 2026-05-05-pm (Run 14)

## Active
- **Wire golden eval harness to CI** — Create `.github/workflows/lead-qualifier-eval.yml`, Monday weekly cron + PR trigger. Add `LEAD_QUALIFIER_AGENT_ID` GH Secret. Closes Issue #110.
- **Bonus: Wire check_project_invariants.py into pre-commit (run 8)** — Em-dash blocker cleared today (8f680e8). Add Check 10 (10-line bash block). Closes run 8, drops pending 3→2.

## Still Pending (active_directions, awaiting human approval)
- **AI-to-Human Handoff v1** (run 4, 2026-04-16) — pending 19 days. M-effort. Infrastructure exists. Critical customer gap.
- **Widget 3-Copy Sync Guard** (run 7, 2026-04-24) — pending 11 days. `scripts/check-widget-sync.sh` not yet created. S-effort.
- **Wire check_project_invariants.py into pre-commit** (run 8, 2026-04-25) — pending 10 days. Blocker cleared today. S-effort.

## Parking Lot (survived debate but not chosen this run)
- **Fix email_sequences N+1 queries** (ROI 2.3, GH #112) — WEAKENED. Valid issue but email adoption not at scale. Issue tracked.
- **Extract _process_pending_sends()** (ROI 1.8, GH #113) — Did not debate. Tracked in issue. Promote if email router hits 1500+ lines.
- **Fix KB broken wikilinks / orphaned articles** (new, from kb-health.py) — 11 orphaned articles, 13 broken wikilinks. S-effort. Promote if KB query accuracy degrades.
- **Wire golden eval harness to weekly CI** — WINNER this run.
- **Onboarding V2 characterization tests** (ROI 1.7) — Pre-condition: first sprint issue complete.
- **widget_helpers Split Smoke Tests** (ROI 2.0) — Still deferred pending Playwright confirmation.
- **Stripe Billing Smoke Tests** (ROI 2.2) — Promote next pricing sprint.

## Rejected This Run
- **AI-to-Human Handoff v1 (as run 14 winner)** — KILLED. Already in active_directions. No new evidence since run 4. M-effort. Re-recommending would increase pending queue, not reduce it.
- **Fix email N+1 (as run 14 winner)** — WEAKENED. Real but non-urgent. Issue tracked. Adoption hasn't scaled to pain point.

## Governance Corrections This Run
- **Run 13 IMPLEMENTED** (72f8204): AdminAnalyticsPage.jsx 6 silent catches fixed + pre-commit Check 9 added. Moratorium lifted: 4→3 pending.
- **SettingsPage.jsx split DONE** (27e06f0): Parking lot ROI 1.9 item complete. Remove from parking lot.
- **Em-dash blocker CLEARED** (8f680e8): WizardStepAutoKB.jsx + AutomationActivityCard.jsx fixed. check_project_invariants.py passes all 6 checks. Run 8 implementation unblocked.

## Questions for Next Run (Run 15)
1. Was `.github/workflows/lead-qualifier-eval.yml` created and does the first run pass? (check commit log)
2. Was Check 10 (check_project_invariants.py) added to pre-commit? (closes run 8)
3. Widget 3-Copy Sync Guard (run 7) — still `MISSING`. Has `scripts/check-widget-sync.sh` been created?
4. AI-to-Human Handoff (run 4) — 19 days pending. If still unimplemented at run 15, recommend as moratorium concern.
5. Email N+1 (GH #112) — is email automation being used by any tenants at scale yet?
