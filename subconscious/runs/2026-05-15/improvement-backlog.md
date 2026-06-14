# Improvement Backlog — 2026-05-15 (Run 17)

## Active (moratorium — clear these first)

- **Widget 3-Copy Sync Guard** (run 7, day 21) — create `scripts/check-widget-sync.sh` + wire pre-push + fix CLAUDE.md Invariant #4. S-effort, ~15 min. [WINNER run 17]
- **Wire check_project_invariants.py into pre-commit** (run 8, day 20) — 8-line block. Script passes 6/6. S-effort, ~5 min. [Bonus A]
- **Wire lead qualifier golden eval to CI** (run 14, day 10) — create `.github/workflows/lead-qualifier-eval.yml`. S-effort, ~20 min. Closes Issue #110. [Bonus B]
- **AI-to-Human Handoff v1** (run 4, day 29) — explicit-trigger-only, M-effort, 1.5-2 days. Cannot be auto-implemented. Requires deliberate sprint allocation. [URGENT — oldest pending, critical for all industries]

## Run 18 Mandate

> **IF Widget 3-Copy Sync Guard still unimplemented at run 18:** Run 18 winner MUST be **Automated Moratorium Escalation Hook** — modify `nightly-commit-review.sh` to auto-create GH comments on oldest pending issues when moratorium active + age > 14 days. "4 consecutive moratorium runs with same winner" threshold is reached at run 18.

## Parking Lot (survived debate / deferred)

**After moratorium exits (post-implementation of runs 7+8+14):**
- **Automated Moratorium Escalation Hook** (workflow, ROI 1.8) — WEAKENED this run (premature at run 3). Modify `nightly-commit-review.sh` to create GH comments on oldest pending issues when moratorium active. Mandated for run 18 if Widget Sync Guard still unimplemented.
- **Zapier API key plan_status enforcement** (issue #107, day 15, ROI 2.5) — KILLED (moratorium + wrong queue). Route via issue-to-pr-loop. First code fix after moratorium exits.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — `list_enrollments` 1001 queries per 1000 enrollments. Bulk `.in_()` fix. M-effort.
- **Stripe billing smoke tests** (ROI 2.2) — 821f660 touched 16 billing files, zero QA. Revisit next pricing sprint.
- **widget_helpers.py smoke tests** (ROI 2.0) — 3 modules, 1 call each. Production-verified 23 days, clean hygiene item.
- **Bug-patterns.md split by month** (ROI 1.8, 2379 lines) — Split into monthly files + INDEX.md. Update nightly auto-logger path.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8) — 120-line duplication in email_sequences.py.
- **Onboarding V2 characterization tests** (ROI 1.7) — POST /api/onboarding/start, complete_step, get_wizard_state.
- **California AI companion disclosure audit** (ROI 1.6) — SB 243 + companion chatbot law. Low-effort compliance check.

## Rejected This Run

- **Zapier API key plan_status enforcement** (KILLED — moratorium + GH#107 already tracked + wrong queue)
- **Automated Moratorium Escalation Hook** (WEAKENED → parking lot — sound meta-fix, premature at run 3 of same winner; mandated for run 18 if same winner)

## Questions for Next Run (Run 18)

1. **Is Widget 3-Copy Sync Guard implemented?** If NO → winner is Automated Moratorium Escalation Hook (mandatory boundary condition set this run). If YES → moratorium may exit (pending drops 4→3 or lower). Report implementation count.
2. **Is Zapier issue #107 still open?** If moratorium exits, this is first code fix via issue-to-pr-loop.
3. **Has AI-to-Human Handoff (run 4, 29+ days) been sprint-allocated?** If not, flag it as CRITICAL — it cannot be auto-implemented but is the oldest pending item.
4. **Nightly reviews May 13-15 show zero code commits.** Is there a project pause (holiday, workload), or is implementation capacity genuinely blocked? Answer changes the diagnosis.
