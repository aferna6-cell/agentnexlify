# Improvement Backlog — 2026-04-30

## Active
- **JS Silent Catch Pre-commit Guard** (run 3, 19 days pending) — Add Check 9 to `scripts/hooks/pre-commit`. Grep staged `.js`/`.jsx` for `.catch(() => null)` / `.catch(() => {})`. Block without inline override. Fix 2 violations first (`MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`). S-effort.

## Parking Lot (survived debate, not chosen)

| Idea | Age | Effort | ROI | Note |
|------|-----|--------|-----|------|
| Widget 3-Copy Sync Guard (run 7) | 6 days | S | 2.2 | Create `scripts/check-widget-sync.sh` + pre-push wire. Promote to run 10 winner if run 3 clears. |
| AI-to-Human Handoff v1 (run 4) | 14 days | M | 2.5 | Critical gap all 7 industries. M-effort deferred by moratorium protocol. Promote after moratorium lifts. |
| Pre-fix em-dash + wire check_project_invariants.py (run 8) | 5 days | S+S | 2.3 | 2-step: fix WizardStepAutoKB.jsx:140/172/254 em-dash violations first, then wire script to pre-commit. |
| widget_helpers Split Smoke Tests | — | S | 2.0 | Write `backend/tests/test_widget_helpers_smoke.py`: import each of 3 modules + call one function. Verifies 6cf4646 refactor is clean. |
| Widget Hot-Zone Regression Suite | — | M | 2.1 | Confirm Playwright (`npx playwright install` succeeds) before promoting. |
| Stripe Billing Smoke Tests | — | M | 2.2 | 821f660 touched 16 billing files, zero QA. Plan-tier contract tests. Revisit next pricing sprint. |
| Bug-patterns.md Split by Month | — | S | 1.8 | File at 2200+ lines. Split into monthly files + INDEX.md. |
| Small Business SaaS KB Seed | — | S | 1.5 | /kb-discover on 3 SMB queries, fill sparse category. |

## Rejected This Run
None killed outright — moratorium mode focuses on age-sorted pending implementation, not fresh rejection.

## Run 2 Winner Status Correction
**Lead Source Analytics Chart** (run 2, 2026-04-06) — Status corrected from `pending_approval` to `implemented_unverified`. `AnalyticsPage.jsx` lines 909–913 confirmed: full Recharts `BarChart` with `fetchLeadSources` API call and state management. Git history shows implementation predates this run. Governance.json updated accordingly.

## Questions for Next Run (Run 10)
1. Has the JS Silent Catch guard been wired? If yes, moratorium count drops to 3 — moratorium lifts. What does run 10 do without moratorium?
2. Is Widget Hot-Zone Playwright suite unblocked? (`npx playwright install` status?)
3. Any new customer feedback on AI-to-Human Handoff urgency? GoHighLevel announced anything that changes the competitive calculus?
4. Did WizardStepAutoKB.jsx em-dash violations get fixed (prerequisite for run 8 winner)?
