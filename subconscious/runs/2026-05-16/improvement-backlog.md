# Improvement Backlog — 2026-05-16 (Run 19)

## Active (moratorium — clear these first)

- **[WINNER run 19]** Formally encode Moratorium Escalation Protocol in
  `.claude/skills/nightly-commit-review/SKILL.md` — add "## Moratorium Escalation Protocol"
  section + step 9A in Scheduled Task Prompt. Content pre-written in
  `subconscious/runs/2026-05-15-pm/winning-concept.md`. ~10 min.

- **Automated Moratorium Escalation Hook** (run 18, day 0) — GH issue #169 created
  today via improvised behavior. SKILL.md not formally updated (run 18 = partially
  implemented). Run 19 winner completes it.

- **Wire golden eval harness to CI** (run 14, day 11) — create
  `.github/workflows/lead-qualifier-eval.yml`. S-effort, ~20 min. Closes Issue #110.

- **Wire check_project_invariants.py into pre-commit** (run 8, day 21) — 8-line block;
  script passes 6/6. S-effort, ~5 min.

- **Widget 3-Copy Sync Guard** (run 7, day 22) — create `scripts/check-widget-sync.sh`
  + wire pre-push + fix CLAUDE.md Invariant #4. S-effort, ~15 min. [Bonus A]

- **AI-to-Human Handoff v1** (run 4, day 30) — explicit-trigger-only, M-effort, 1.5-2 days.
  Requires deliberate sprint allocation. Cannot be auto-implemented. [URGENT — oldest
  pending, Critical cross-industry gap]

**GH escalation:** Issue #169 open (created 2026-05-16 by nightly review). Daily updates
once SKILL.md formalized.

**60-min sprint exits moratorium (pending 5→1):** runs 19 + 8 + 7 + 14 (~50 min total).
Implementation sketches all in `subconscious/runs/2026-05-15-pm/winning-concept.md`.

---

## Parking Lot (survived debate / deferred)

**After moratorium exits (post-implementation of runs 7+8+14):**

- **Create ai-ready GH Issues for S-effort items (runs 7+8+14)** — route to
  issue-to-pr-loop. ROI: moratorium exits autonomously IF loop is running.
  WEAKENED this run (loop-running uncertainty). Promote to run 20 winner if SKILL.md
  update doesn't produce sustained GH pressure within 48h.
- **Zapier API key plan_status enforcement** (issue #107, ROI 2.5, HIGH security) —
  first post-moratorium code fix. Route via issue-to-pr-loop.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — bulk `.in_()` fix.
- **Stripe billing smoke tests** (ROI 2.2) — zero QA after 821f660 (16 billing files).
- **Bug-patterns.md split by month** (ROI 1.8, 2379 lines).
- **Extract _process_pending_sends()** (GH #113, ROI 1.8).
- **Onboarding V2 characterization tests** (ROI 1.7).
- **California AI companion disclosure audit** (ROI 1.6) — SB 243.
- **Governance threshold reduction (max_pending 3→2)** — prevents future 5-item buildup.
  Defer: governance parameter changes lower priority than clearing current moratorium.
- **GitHub milestone for moratorium exit sprint** — consolidates all 5 pending items.
  Defer: GH #169 already provides this visibility.

---

## Rejected This Run

- **Widget 3-Copy Sync Guard as winner** — KILLED as winner candidate (sixth consecutive
  recommendation with no new evidence; two stronger alternatives). Remains Bonus A.
  Already visible in GH #169 pending table.

---

## Questions for Next Run (Run 20)

1. **Is nightly-commit-review SKILL.md updated?** Read `.claude/skills/nightly-commit-review/SKILL.md`.
   If "## Moratorium Escalation Protocol" section present → run 19 implemented.
   If missing → third consecutive partial-implementation run; escalate governance threshold.

2. **Did next nightly review (2026-05-17) comment on GH #169?** Check issue comments.
   If YES: mechanism is operational. First post-mechanism winner: recommend Idea 2 (ai-ready issues)
   or Widget Sync Guard.
   If NO: SKILL.md still not updated; repeat run 19 recommendation.

3. **Any of runs 7+8+14 implemented since today?** Each drops pending count. Track:
   - pending ≤ 3 → moratorium exits, free-choice runs resume
   - pending = 1 → escalate run 4 to sprint allocation issue

4. **Is issue-to-pr-loop actively running?** Check git log for commits with `[auto-nightly]`
   or `[issue-to-pr-loop]` tags. If confirmed running, Idea 2 (ai-ready issues) is
   high-confidence for run 20 winner.

5. **GH #169 status?** If closed without implementation: immediately re-open or create new
   moratorium issue. If assigned to someone: note sprint start.
