# Improvement Backlog — 2026-05-11 (Run 16)

## Active (moratorium — clear these first)

- **Widget 3-Copy Sync Guard** (run 7, day 17) — create `scripts/check-widget-sync.sh` + wire pre-push + fix CLAUDE.md Invariant #4. S-effort, ~15 min. [WINNER run 16]
- **Wire check_project_invariants.py into pre-commit** (run 8, day 16) — 8-line block. Script passes 6/6. S-effort, ~5 min. [Bonus A]
- **Wire lead qualifier golden eval to CI** (run 14, day 6) — create `.github/workflows/lead-qualifier-eval.yml`. S-effort, ~20 min. Closes Issue #110. [Bonus B]
- **AI-to-Human Handoff v1** (run 4, day 25) — explicit-trigger-only, M-effort, 1.5-2 days. Cannot be auto-implemented. Requires deliberate sprint allocation. [URGENT — oldest pending]

## Parking Lot (survived debate but not chosen / deferred)

**To implement after moratorium exits (non-moratorium runs):**
- **Zapier API key plan_status enforcement** (issue #107, 11 days open, ROI ~2.5) — route via issue-to-pr-loop, NOT subconscious. Add plan_status filter in `_get_api_key_client`, regression test for cancelled tenant auth. HIGH security priority. Promote to FIRST code fix after moratorium.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — `list_enrollments` 1001 queries per 1000 enrollments. Bulk `.in_()` fix. M-effort.
- **widget_helpers.py smoke tests** (ROI 2.0) — 3 modules, 1 call each. Closes `implemented_unverified` governance status for run 5. Status: production-verified after 23 days, but smoke tests are clean hygiene.
- **Stripe billing smoke tests** (ROI 2.2) — 821f660 touched 16 billing files, zero QA. Plan-tier contract tests. Revisit next pricing sprint.
- **Onboarding V2 characterization tests** (ROI 1.7) — POST /api/onboarding/start, complete_step, get_wizard_state. Prevents implemented_unverified for V2 sprint.
- **Bug-patterns.md split by month** (ROI 1.8) — 2379 lines (was 2204 in run 7). Auto-logger writes to it. Split into monthly files + INDEX.md.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8) — 120-line duplication in email_sequences.py. M-effort.
- **California AI companion disclosure audit** (ROI 1.6) — SB 243 + companion chatbot law in effect. Low-effort compliance check.
- **Automated moratorium escalation hook** (workflow) — when moratorium active + oldest pending > 14 days, nightly review auto-creates GH comment on oldest pending issue. Closes feedback loop between recommendation and implementation. Not chosen this run (moratorium), but high-value workflow improvement.

## Rejected This Run

- **Zapier API key plan_status enforcement** (KILLED — moratorium + GH#107 already tracked + wrong queue for targeted bug fix)
- **widget_helpers.py smoke tests** (KILLED — moratorium + 23 days production use = effectively verified)

## Questions for Next Run

1. If run 17 arrives and Widget 3-Copy Sync Guard is STILL unimplemented: consider whether the subconscious should recommend the "Automated moratorium escalation hook" idea (Idea 5 this run) as a meta-improvement to break the pattern. At 4 consecutive moratorium runs with the same winner, the system mechanism is worth questioning.
2. Is issue #107 (Zapier API key) still open? If moratorium exits, this should be run 17's winner.
3. Has the Onboarding V2 sprint introduced any `implemented_unverified` items that need characterization tests?
