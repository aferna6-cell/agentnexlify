# Improvement Backlog — 2026-04-18-pm

## Active
- **Split `widget_helpers.py` into chat/lead/booking modules** — backend/routers/, update 4 callers atomically (code_health, Effort: M, ROI 2.1)

## Prior Active (pending approval — not yet implemented)
- **JS Silent Catch Pre-commit Guard** (run 3, 2026-04-11) — extend `scripts/hooks/pre-commit` Check 8 to warn on `.catch(() => null/{})`

## Parking Lot (survived debate but not chosen)

| Idea | ROI | Note |
|------|-----|------|
| SettingsPage.jsx split | 1.9 | L effort, no active bugs, no sprint context. Revisit when next settings feature ships. |
| Migration Number Collision Guard | 1.6 | S effort, same mechanism as run 3. Bundle with run 3 pre-commit changes when approved. |
| Widget Click Regression Guard (Playwright E2E) | 2.0 | Playwright infra unconfirmed. Verify `npx playwright install --check` first. |
| Managed Agents Automated Integration Tests | 1.5 | Expand `backend/tests/test_managed_agents.py` to all 5 HTTP endpoints. |
| Onboarding AI Parser Edge Case Tests | 1.5 | `lead-parser-replacement_spec.md` committed; write tests before replacement begins. |
| Ingest 5 Competitor Briefs into KB | 1.2 | Locate files from commit `b97928a` first, then `/kb-ingest x5`. |
| Widget Hot-Zone Regression Suite | 2.1 | **Now unblocked by this run's winner.** Promote to winner candidate next run. |
| Migration Safety Net Pre-Push Check | 1.8 | Apply-friction is the real bottleneck. Add after apply-migration helper exists. |
| TCPA/State AI Law Compliance Checklist | 1.4 | Research exists (`89617d7`), no active legal exposure found. Valuable but not urgent. |
| Fix health-check.sh morning grep drift | 1.3 | `find` vs glob expansion. Self-monitoring reliability. S effort. |

## Rejected This Run

| Idea | Reason |
|------|--------|
| SettingsPage.jsx split (as winner) | L effort, React state sharing risk, no active bugs driving it, no current sprint context for Settings. Parked. |
| Migration collision guard (as winner) | S effort but same mechanism as run 3 (pre-commit extension). Low-frequency trigger. Parked, not rejected — revisit when run 3 approved. |

## Questions for Next Run

1. Has `widget_helpers.py` split been approved and executed? If yes, is Widget Hot-Zone Regression Suite (parking lot ROI 2.1) now the obvious winner?
2. Has JS Silent Catch guard (run 3, pending approval since 2026-04-11) been applied? If still pending after 3 runs, is there a blocker to surface?
3. Did the business-personalization sprint introduce any new `widget_helpers.py` concerns that the split plan needs to account for?
4. Has the Supabase MCP auth (401) been fixed? Schema cross-check is DEFERRED for 2+ sessions — this blocks Pass 4 of architecture audits.
