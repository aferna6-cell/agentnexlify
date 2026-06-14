# Improvement Backlog — 2026-05-16-pm (Run 20)

## Active (moratorium — clear these first)

- **[WINNER run 20]** Governance Escalation: reduce max_pending_approvals 3→2 in governance.json
  + create GH milestone "Moratorium Exit Sprint" with 4 S-effort issues (runs 19/8/7/14). ~32 min.
  Per run 19 binding mandate. Implementation sketch in this run's winning-concept.md §Steps 1-3.

- **[Bonus Step 0]** SKILL.md Moratorium Escalation Protocol (run 19, day 0) — add "## Moratorium
  Escalation Protocol" + step 9A to `.claude/skills/nightly-commit-review/SKILL.md`. ~10 min.
  Pre-written in subconscious/runs/2026-05-15-pm/winning-concept.md §Steps 1-2. Do alongside
  run 20 winner — prerequisite for sustained daily GH escalation loop.

- **Wire lead qualifier eval to CI** (run 14, day 11) — `.github/workflows/lead-qualifier-eval.yml`.
  S-effort, ~20 min. [Part of Moratorium Exit Sprint milestone]

- **Wire check_project_invariants.py into pre-commit** (run 8, day 21) — 8-line call block.
  S-effort, ~5 min. [Part of Moratorium Exit Sprint milestone]

- **Widget 3-Copy Sync Guard** (run 7, day 22) — `scripts/check-widget-sync.sh` + pre-push wire
  + CLAUDE.md Invariant #4 fix. S-effort, ~15 min. [Part of Moratorium Exit Sprint milestone]

- **AI-to-Human Handoff v1** (run 4, day 30) — explicit-trigger-only, M-effort, 1.5-2 days.
  Sprint allocation required. Cannot be S-effort auto-implemented. [URGENT — oldest pending,
  Critical cross-industry gap, parallel track independent of moratorium]

**GH escalation:** Issue #169 open. Milestone "Moratorium Exit Sprint" to be created (run 20 winner).

**~50-min sprint exits moratorium (pending 5→1):** runs 19 + 8 + 7 + 14 total. All implementation
sketches pre-written in subconscious/runs/2026-05-15-pm/winning-concept.md.

---

## Parking Lot (survived debate / deferred)

**After moratorium exits:**

- **Tag runs 7+8+14 as ai-ready GH issues** — WEAKENED run 20 (loop-running unconfirmed; conditional
  promotion from run 19 doesn't clearly fire). Promote when loop confirmed via
  `git log --grep 'issue-to-pr-loop' --since='7 days ago'` returning production commits.
- **Sprint allocation issue for run 4 (AI-to-Human Handoff)** — considered run 20, not debated (out
  of moratorium scope). Create in run 21 as parallel track regardless of moratorium status.
- **Zapier API key plan_status enforcement** (issue #107, ROI 2.5, HIGH security) — first
  post-moratorium code fix. Route via issue-to-pr-loop.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3).
- **Stripe billing smoke tests** (ROI 2.2).
- **Bug-patterns.md split by month** (ROI 1.8, 2379 lines).
- **Extract _process_pending_sends()** (GH #113, ROI 1.8).
- **Onboarding V2 characterization tests** (ROI 1.7).
- **California AI companion disclosure audit** (ROI 1.6).

---

## Rejected This Run

- **Repeat run 19 SKILL.md recommendation as standalone winner** — KILLED. Third consecutive
  same-mechanism meta-fix with no new force for implementation. Freeze threshold (3 rejections → frozen)
  would fire incorrectly if this idea keeps being repeated. Subsumed as Bonus Step 0 in run 20
  implementation sketch — recommendation preserved, not abandoned.

---

## Questions for Next Run (Run 21)

1. **Was GH milestone "Moratorium Exit Sprint" created?** Check GH milestones. If YES and any issue
   in it closed → moratorium trending toward exit. If NO → governance mandate stall at meta; open P0
   blocker issue.

2. **Was governance.json max_pending_approvals updated 3→2?** Read config block. If still 3 → not
   implemented. Note: changing to 2 fires moratorium even sooner on next accumulation.

3. **Did any of runs 7+8+14+19 get implemented since run 20?** Count pending_approval items:
   - pending ≤ 3 → moratorium exits; free-choice runs resume
   - pending = 1 → only run 4 remains; escalate sprint allocation

4. **Is issue-to-pr-loop confirmed running?**
   `git log --oneline --grep 'issue-to-pr-loop' --since='7 days ago'`
   If YES: promote ai-ready issues (Idea 4) to run 21 winner regardless of moratorium.
   If NO: loop status is still uncertain; don't create ai-ready issues yet.

5. **Run 4 now 31+ days.** Any sprint allocation signal? Check GH for new issues/PRs referencing
   "AI-to-Human Handoff" or "handoff" in title. If none: create dedicated sprint-allocation issue in
   run 21 (parallel track, doesn't wait for moratorium exit).
