# Improvement Backlog — 2026-05-01 (Run 12)

## Active (Moratorium — Oldest Pending First)

- **JS Silent Catch Guard — Check 10 + AdminAnalyticsPage fix** (run 3, day 24+) — Fix 6 silent catches in AdminAnalyticsPage.jsx:117-122; add Check 10 to pre-commit. S-effort. Zero blockers. Closes Issue #109.

## Pending Approval (implement to lift moratorium)

| Run | Title | Age | Effort | Blocker |
|-----|-------|-----|--------|---------|
| Run 3 | JS Silent Catch Guard (Check 10) | 24 days | S | None |
| Run 4 | AI-to-Human Handoff v1 | 15 days | M | None |
| Run 7 | Widget 3-Copy Sync Guard | 7 days | S | None |
| Run 8 | Wire check_project_invariants.py | 6 days | S+S | Em-dash scope fix first |

**Moratorium lifts when pending count ≤ 3.** Run 3 implementation alone drops to 3 → moratorium lifts.

## Parking Lot (survived debate, post-moratorium candidates)

Priority order for run 13+:
1. **Wire golden eval harness to CI** (Issue #110, ROI 2.5) — `.github/workflows/lead-qualifier-eval.yml` with Monday cron. First post-moratorium winner. Requires `LEAD_QUALIFIER_AGENT_ID` in GH Secrets.
2. **Scope em-dash check + Wire check_project_invariants.py** (run 8 unblocking, ROI 2.3 after fix) — Update `check_project_invariants.py` em-dash check to skip `.jsx/.tsx` files (false positives from UI render chars), then wire into pre-commit as Check 11. Two-step M-effort.
3. **Onboarding V2 characterization tests** (ROI 1.7) — Write `backend/tests/test_onboarding_characterization.py` before first sprint issue merges.
4. **Bug-patterns.md split by month** (ROI 1.8) — 2320 lines, god-class threshold exceeded (Rule 9 = 600 lines). Split into monthly files + INDEX.md.
5. **Widget 3-Copy Sync Guard** (run 7 winner, ROI 2.1) — Create `scripts/check-widget-sync.sh` + wire into pre-push.
6. **Stripe billing smoke tests** (ROI 2.2) — billing constants harness + plan-tier contract tests. Revisit next pricing sprint.
7. **widget_helpers Split Smoke Tests** (ROI 2.0) — Import + call one function from each of 3 split modules.
8. **SettingsPage.jsx split** (ROI 1.9) — Revisit when next settings feature ships.
9. **Small Business SaaS KB Seed** (ROI 1.5) — 3 articles via /kb-discover.

## Rejected This Run

- **Wire golden eval harness** — KILLED (moratorium forbids parking lot; run 13 candidate)

## Questions for Next Run

1. Has JS Silent Catch Guard (run 3) been implemented? If yes, moratorium lifts — proceed to golden eval harness CI wiring.
2. Has the em-dash scope fix in `check_project_invariants.py` been applied? This unblocks run 8 (wire invariants.py into pre-commit).
3. Has Onboarding V2 sprint started? If sprint commit count > 3, characterization tests become urgent (implemented_unverified risk).
4. Is `LEAD_QUALIFIER_AGENT_ID` provisioned in GH Secrets? Required before wire eval harness can be implemented.
