# Improvement Backlog — 2026-05-04 (Run 13)

## Active (Moratorium-Mandated)
- **JS Silent Catch Guard — Check 10 + AdminAnalyticsPage.jsx fix** (run 3/9/10/11/12/13, day 24+) — S-effort, copy-paste-ready. Implementing lifts moratorium: pending 4 → 3.

## Pending Approval (Pre-Moratorium Winners — implement these)
- **Wire check_project_invariants.py into pre-commit** (run 8, 2026-04-25) — BLOCKED by em-dash false positives. Unblock path: scope em-dash check to skip .jsx/.tsx (1-line fix in check_project_invariants.py). After fix: add as Check 11 to pre-commit. S-effort.
- **Widget 3-Copy Sync Guard** (run 7, 2026-04-24) — create scripts/check-widget-sync.sh + wire into pre-push + update CLAUDE.md Invariant #4 (2→3 paths). S-effort. Never created.
- **AI-to-Human Handoff v1** (run 4, 2026-04-16) — explicit-trigger-only, 1.5-2 days. Infrastructure exists. Critical gap across all 7 industries. M-effort.

## Parking Lot (Post-Moratorium Candidates)
- **Wire golden eval harness to CI** (2026-04-30-pm, ROI 2.5, Issue #110) — `backend/tests/evals/` added 7854ede, Monday cron .github/workflows/lead-qualifier-eval.yml needed. Requires LEAD_QUALIFIER_AGENT_ID in GH Secrets. **PROMOTE AS RUN 14 WINNER when moratorium lifts.**
- **Fix email_sequences N+1 queries** (2026-05-04, ROI 2.3, Issue #112) — list_enrollments: 1001 queries per 1000 enrollments; list_sequences: 2 calls per sequence. Bulk .in_() fix. M-effort. Promote run 15 or when email automation adoption grows.
- **Onboarding V2 characterization tests** (2026-04-30-pm, ROI 1.7) — write backend/tests/test_onboarding_characterization.py before V2 sprint issues ship. Covers POST /api/onboarding/start, complete_step, get_wizard_state.
- **Extract _process_pending_sends() from email_sequences.py** (2026-05-04, ROI 1.8, Issue #113) — ~120 lines of duplicated per-send loop logic between process_sequences and run_sequence_processor. M-effort.
- **widget_helpers Split Smoke Tests** (2026-04-25, ROI 2.0) — only `implemented_unverified` governance item. Write backend/tests/test_widget_helpers_smoke.py: import each of 3 modules + call one function.
- **Stripe Billing Smoke Tests / Plan-Tier Contract Tests** (2026-04-24, ROI 2.2) — 821f660 touched 16 billing files, zero QA. Billing constants harness + plan-tier contract tests.
- **Bug-patterns.md Split by Month** (2026-04-24, ROI 1.8) — 2,320+ lines. Split into monthly files + INDEX.md.
- **Small Business SaaS KB Category Seed** (2026-04-20, ROI 1.5) — /kb-discover on 3 SMB queries.
- **Fix health-check.sh morning grep drift** (2026-04-18, ROI 1.3) — find vs glob in scripts/daily/health-check.sh.
- **Moratorium Governance Self-Enforcing Threshold** (2026-04-25, ROI 1.6) — auto-trigger logic needs wiring into SKILL.md Phase 5 synthesis gate.
- **Widget Hot-Zone Regression Suite** (2026-04-18, ROI 2.1) — BLOCKED on Playwright confirmation.
- **California AI Companion/Chatbot Disclosure Review** (2026-05-04, ROI 1.6) — KB now has SB 243 + Perkins Coie articles. Widget chat may require disclosure if it provides guidance/support. Low effort audit.

## Rejected This Run
- **Wire golden eval harness to CI** — KILLED by moratorium (parking lot explicitly says "post-moratorium winner"). Not a rejection of the idea — governance gate.
- **Extract _process_pending_sends()** — KILLED by moratorium + no urgency signal yet.

## Questions for Next Run (Run 14)
1. Was JS Silent Catch Guard (Check 10) implemented? If yes, moratorium lifts — run 14 winner should be **Wire golden eval harness to CI** (highest parking lot ROI 2.5).
2. Was the em-dash scope fix applied? If yes, run 8 can be implemented in the same session.
3. Has email automation (email_sequences.py) gained adoption? Any tenants with 100+ enrollments? If yes, N+1 fix becomes urgent.
4. Do California AI companion/chatbot laws (SB 243 + Perkins Coie) apply to AgentNexLiFy's widget? Needs legal review of disclosure requirements.
