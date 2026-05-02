# Improvement Backlog — 2026-05-02 (Run 13)

## Active
- **JS Silent Catch Check 10 + AdminAnalyticsPage.jsx fix** — Fix 6 `.catch(() => null)` in AdminAnalyticsPage.jsx:117-122 + Add Check 10 to scripts/hooks/pre-commit. S-effort. Closes Issue #109. Lifts moratorium (4 → 3 pending). [Run 3 winner, day 21]

## Pending Approval (moratorium queue — oldest first)

1. **JS Silent Catch Check 10** ← this run's winner (run 3 original, 2026-04-11, day 21)
2. **Wire check_project_invariants.py into pre-commit** (run 8, 2026-04-25) — BLOCKED: em-dash scope fix prerequisite still needed
3. **Widget 3-Copy Sync Guard** (run 7, 2026-04-24) — script not yet created
4. **AI-to-Human Handoff v1** (run 4, 2026-04-16) — infrastructure exists, M-effort

## Parking Lot (survived moratorium; deploy when moratorium lifts)

| Title | ROI | Notes |
|-------|-----|-------|
| Wire golden eval harness to CI | 2.5 | Issue #110 open. First post-moratorium winner. Run 14 candidate. |
| Stripe Billing Smoke Tests | 2.2 | 821f660 touched 16 billing files, zero QA. Revisit next pricing sprint. |
| Widget Hot-Zone Regression Suite | 2.1 | Playwright needed. widget_helpers split done. |
| widget_helpers Split Smoke Tests | 2.0 | Easiest regression insurance on implemented_unverified item. |
| Spec Symbol Validation Hook | 2.0 | Needs hook enforcement, not just skill doc update. |
| Onboarding V2 Characterization Tests | 1.7 | Write before first sprint issue merge. |
| Scope em-dash + Wire invariants.py | 1.9 | Prerequisite to run 8; one-line fix + wiring. Run 15 candidate. |
| Bug-patterns.md Split by Month | 1.8 | 2,320+ lines now. Auto-logger needs path update. |
| Migration Safety Net Pre-Push Check | 1.8 | Revisit when apply-migration helper exists. |
| Reasoning-trace Comment Scanner | 1.5 | Daily log P2. Warn-only pre-commit scan for `// Step N:` markers. |
| Small Business SaaS KB Seed | 1.5 | 3 articles via /kb-discover. |

## Rejected This Run
- **email_sequences N+1 query fix** — Already in GH #112 (nightly review). Moratorium forbids adding new items. Correct handling: implement via backend-dev through the GH issue.
- **em-dash scope + wire invariants.py (as standalone)** — Belongs as blocker note on run 8 active direction, not a separate subconscious recommendation.
- **Wire golden eval harness to CI** — Moratorium violation; promote to run 14 winner.
- **Reasoning-trace comment scanner** — Moratorium violation; parking lot.

## Questions for Next Run (Run 14)
1. Has JS Silent Catch (run 3) been implemented? If yes: moratorium lifts → golden eval harness CI is run 14 winner.
2. If JS Silent Catch still unimplemented: escalate to human with direct implementation offer (`/subconscious --implement`).
3. Has em-dash scope fix been applied? If yes: run 8 (Wire invariants.py) is unblocked.
4. Did Onboarding V2 sprint generate any new silent catches (new JSX files without Check 10 guard)?
5. Has email_sequences N+1 (Issue #112) been addressed — or is it expanding to other routers?
