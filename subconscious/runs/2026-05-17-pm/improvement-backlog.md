# Improvement Backlog — 2026-05-17-pm (Run 22)

## Active

### Winner: Run 22
**Wire check_project_invariants.py into pre-commit as Check 10**
- Run 8 mandate (22 days stale)
- Script: `scripts/check_project_invariants.py` — stdlib-only, passes all 6 checks
- Integration: 3 lines in `scripts/hooks/pre-commit` after Check 9
- Effort: ~5 min
- Evidence: em-dash blocker cleared May 5. Pre-commit has 9 checks. Check 10 slot ready.
- Implementation sketch: winning-concept.md §Steps 1-3

### Immediate next sprint (~45 min, drops pending 6→3 = moratorium exits)

| Run | Item | Min | Sketch |
|-----|------|-----|--------|
| 19 | Add Moratorium Escalation Protocol to nightly-commit-review SKILL.md | 10 | `subconscious/runs/2026-05-16/winning-concept.md` §Steps 1-2 |
| 7 | Create scripts/check-widget-sync.sh + wire pre-push + fix CLAUDE.md Invariant #4 | 15 | `subconscious/runs/2026-05-15-pm/winning-concept.md` |
| 14 | Create .github/workflows/lead-qualifier-eval.yml | 20 | Prior winning-concept |

Together with run 22 winner: 50 min total, pending 7→3, moratorium exits.

### Moratorium S-effort summary (full list)

| Run | Item | Days | Effort | Status |
|-----|------|------|--------|--------|
| 8 | Wire check_project_invariants.py (THIS WINNER) | 22 | 5 min | pending |
| 19 | SKILL.md Moratorium Escalation Protocol | 1 | 10 min | pending |
| 7 | Widget 3-Copy Sync Guard | 23 | 15 min | pending |
| 14 | Wire lead qualifier eval to CI | 12 | 20 min | pending |
| 4 | AI-to-Human Handoff v1 (M-effort) | 32 | 1.5 days | pending |
| 21 | Create AI-to-Human Handoff GH Issue | 0 | 15 min | pending |
| 20 | Governance: max_pending 3→2 + milestone | 1 | 2 min | pending |

---

## Parking Lot (survived debate / deferred)

**Idea 1: Restart autopilot-issue-loop + tag S-effort items as ai-ready**
- Debate: WEAKENED — valid but execution uncertain. Loop config unverified.
- Action when ready: Check `.github/workflows/issue-to-pr.yml` is configured. Add `ai-ready`
  label to GH issues for runs 7+8+14+19. If loop picks them up: 4 items auto-cleared.
- Pre-condition: confirm loop has run at least once in git log.

**AI-to-Human Handoff GH Issue (run 21 winner)**
- Implementation sketch fully written: `subconscious/runs/2026-05-17/winning-concept.md`
- Create GH issue "[P0] AI-to-Human Handoff v1" using that sketch
- Does not need another subconscious run to authorize — run 21 sketch is complete and approved
- Do this independently of subconscious cadence

**Zapier API key plan_status enforcement (GH #107, ROI 2.5)**
- HIGH security, 17+ days open
- First post-moratorium code fix candidate
- After moratorium exits (pending ≤ 3): promote to winner

**Fix email_sequences N+1 queries (GH #112, ROI 2.3)**
- 1001 queries per 1000 enrollments
- After moratorium exits

**Bug-patterns.md split by month (2379 lines)**
- Growing daily via auto-logger
- After moratorium exits

---

## Rejected This Run

- **AI-to-Human Handoff GH issue as winner** — WEAKENED. Run 21 (same day) made this exact
  recommendation. Recommending the same thing twice in one day with no new forcing function
  violates the compounding principle. Sketch exists; human can act on it directly without
  subconscious re-recommendation.

- **Autopilot restart as winner** — WEAKENED. Execution uncertainty high. Loop config unverified.
  Manual S-effort items are faster than debugging a potentially unconfigured CI loop.

---

## Questions for Next Run (Run 23)

1. **Was run 22 winner implemented?** Check pre-commit for `check_project_invariants.py` call.
   If YES: pending 7→6. Did the immediate next sprint also happen? (runs 7+14+19 = moratorium exit)
   If NO: governance action fires — reduce max_pending_approvals 3→2 (run 20 mandate, already
   2 runs overdue).

2. **Did run 21 GH issue get created** (AI-to-Human Handoff sprint planning)? Check GH for
   title "AI-to-Human Handoff v1". If YES: proceed to next highest-ROI parking lot item.
   If NO: implementation sketch in runs/2026-05-17/winning-concept.md needs human action.

3. **Moratorium exit status?** pending_approvals ≤ 3 → exit. Moratorium exit = run 23 is free-choice.
   First free-choice: Zapier API key plan_status enforcement (ROI 2.5, GH #107).

4. **Autopilot loop status?** `git log --oneline --grep="issue-to-pr-loop" --since="7 days ago"`.
   Any commits = loop running. If running: tag runs 7+8+14 GH issues as `ai-ready`.

5. **max_pending_approvals**: still 3? Run 20 mandate (3→2) now 2 runs overdue. If run 22+23
   both pass without implementing, governance mandate fires unconditionally in run 23.
