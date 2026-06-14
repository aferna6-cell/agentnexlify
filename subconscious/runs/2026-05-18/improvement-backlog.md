# Improvement Backlog — 2026-05-18 (Run 23)

## Active

- **Moratorium Exit Sprint PR** — Create branch `moratorium-exit-sprint` with all 4 pending
  S-effort items (check_project_invariants pre-commit, widget sync guard, SKILL.md moratorium
  protocol, CI eval workflow). One draft PR = one approval = pending 9→5.
  Sketch: `subconscious/runs/2026-05-18/winning-concept.md`

---

## Parking Lot (survived debate but not chosen)

- **Investigate autopilot-issue-loop status + tag ai-ready** — `ps aux | grep issue-to-pr-loop`
  + GH Actions check. If running: tag GH issues for runs 7, 8, 14, 19 as `ai-ready`. If not:
  create restart issue. High expected value but conditional. First action in next free-choice run.
  ROI: HIGH if loop running, MEDIUM if not.

- **/sprint Slash Command** — `.claude/commands/sprint.md` reads governance.json for pending
  S-effort items and sequences implementation sketches. Correct long-term target after sprint PR
  pattern is established. ROI: 1.6 (medium-term process gain).

- **Auto-Approve Micro-Guard Policy** — `auto_approve_micro_guard: true` for hook/CI/SKILL.md
  additions. Two-phase (governance + SKILL.md). Revisit after moratorium exits and system is
  in steady state. ROI: 1.8 (long-term).

- **AI-to-Human Handoff GH Issue** (run 21 winner, still valid) — Create GH issue with full
  sketch for explicit-trigger handoff v1. ~15 min. Implementation sketch at
  `subconscious/runs/2026-05-17/winning-concept.md`.

- **Email Sequences N+1 Fix** — GH #112. list_enrollments: 1 DB call per enrollment.
  Bulk .in_() fix. M-effort. ROI: 2.3.

- **Zapier API key plan_status enforcement** — GH #107. ROI: 2.5. HIGH security. Route via
  issue-to-pr-loop, NOT subconscious winner queue.

- **AI-to-Human Handoff v1 Feature Build** (run 4, day 33) — M-effort, 1.5-2 days. CRITICAL
  cross-industry gap. Infrastructure exists. Oldest pending item. First candidate after moratorium
  exits.

---

## Rejected This Run

- **check_project_invariants Re-escalation as standalone winner** — subsumed by Idea 1 sprint PR
  as Item A. Not rejected; subsumed.

- **Idea 4 (Auto-Approve Micro-Guard) as this-run winner** — WEAKENED: two-phase dependency,
  premature alongside governance mandate, meta-tooling overhead while production items pending.

- **Idea 5 (Autopilot investigation) as this-run winner** — WEAKENED: conditional branching
  (depends on loop status). Parking lot.

---

## Governance Actions This Run (unconditional — not winner-dependent)

- **Run 20 mandate executed:** `max_pending_approvals` reduced from 3 → 2 in governance.json
- **Pending count updated:** 8 → 9 (run 23 added)

---

## Questions for Next Run

1. **Was the sprint PR created?** If yes: which items were merged? What is the actual pending
   count? If pending ≤ 2 (new threshold): moratorium exits → free-choice run.
2. **Is the autopilot-issue-loop running?** Check `ps aux` + GH Actions. If yes: tag items
   as ai-ready. If no: what broke it?
3. **Is the AI-to-Human Handoff GH Issue created?** Run 21 winner. Pre-written sketch at
   `subconscious/runs/2026-05-17/winning-concept.md §Step 1`.
