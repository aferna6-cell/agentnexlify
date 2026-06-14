# Improvement Backlog — 2026-05-15-pm (Run 18)

## Active (moratorium — clear these first)

- **[WINNER run 18]** Automated Moratorium Escalation Hook — update
  `.claude/skills/nightly-commit-review/SKILL.md` to add Moratorium Escalation Protocol
  section + step 10A in Scheduled Task Prompt. Creates GH issue via mcp__github__ when
  moratorium active + oldest pending > 14 days. ~20 min.

- **Widget 3-Copy Sync Guard** (run 7, day 21) — create `scripts/check-widget-sync.sh`
  + wire pre-push + fix CLAUDE.md Invariant #4. S-effort, ~15 min. [Bonus A — demoted
  from 4-consecutive-winner to bonus]

- **Wire check_project_invariants.py into pre-commit** (run 8, day 20) — 8-line block,
  script passes 6/6. S-effort, ~5 min. [Bonus B]

- **Wire lead qualifier golden eval to CI** (run 14, day 10) — create
  `.github/workflows/lead-qualifier-eval.yml`. S-effort, ~20 min. Closes Issue #110.
  [Bonus C]

- **AI-to-Human Handoff v1** (run 4, day 29) — explicit-trigger-only, M-effort, 1.5-2 days.
  Cannot be auto-implemented. Requires deliberate sprint allocation. [URGENT — oldest
  pending, critical for all 7 industries]

## Parking Lot (survived debate / deferred)

**After moratorium exits (post-implementation of runs 7+8+14):**
- **Zapier API key plan_status enforcement** (issue #107, ROI 2.5, HIGH security) — first
  post-moratorium code fix. Route via issue-to-pr-loop.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — bulk `.in_()` fix.
- **Stripe billing smoke tests** (ROI 2.2) — zero QA after 821f660 (16 billing files).
- **widget_helpers.py smoke tests** (ROI 2.0) — 3 modules, 1 call each.
- **Bug-patterns.md split by month** (ROI 1.8, 2379 lines) — monthly files + INDEX.md.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8) — 120-line duplication.
- **Onboarding V2 characterization tests** (ROI 1.7) — before sprint issues begin.
- **California AI companion disclosure audit** (ROI 1.6) — SB 243 + companion chatbot law.
- **Moratorium Governance Self-Enforcing Threshold** (ROI 1.6) — auto-trigger logic in
  SKILL.md Phase 5 synthesis gate. **Partially fulfilled by run 18 winner** (GH escalation
  is the missing piece; synthesis gate automation still deferred).

## Rejected This Run

- **PR Queue Auto-Merge for Safe Patch Deps** — KILLED: supply chain risk in autonomous
  merge decisions + moratorium protocol override.
- **Email Sequences N+1 Query Fix** — KILLED: moratorium protocol categorical override.
  (Remains in parking lot; promote when pending ≤ 3.)

## Questions for Next Run (Run 19)

1. **Is Automated Moratorium Escalation Hook implemented?** If YES: which GH issue was
   created? Did it produce a human response? If NO: moratorium now at run 5 of same
   meta-winner — re-evaluate governance mechanism.

2. **Are any of Widget Sync Guard (run 7), invariants pre-commit (run 8), or eval CI
   (run 14) implemented?** Each implementation drops pending count. Track:
   - If pending ≤ 3: moratorium exits. First free-choice run since run 8.
   - If pending = 1 (only run 4 remains): escalate run 4 to sprint-allocation issue.

3. **Has AI-to-Human Handoff (run 4, 29+ days) been sprint-allocated or assigned?**
   At 30+ days, this warrants a dedicated GH issue + sprint ticket if none exists.

4. **Did the nightly-commit-review moratorium escalation step actually fire?**
   Check ops/routines/logs/ for "## Moratorium Status" section. If step silently skipped,
   investigate mcp__github__ auth in scheduled context.

5. **Is Zapier issue #107 still open?** If moratorium exits this run, route to
   issue-to-pr-loop immediately.
