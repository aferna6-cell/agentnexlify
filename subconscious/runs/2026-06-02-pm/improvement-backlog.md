# Improvement Backlog — 2026-06-02-pm (Run 47)

## Active

- **Item D AUTONOMOUS-EXECUTABLE** — extend nightly scope to CI YAML creation + mark
  `pending_autonomous` + include inline lead-qualifier-eval.yml (run 47 winner)

## Parking Lot (survived debate but not chosen)

- **GH #181 billing.py fix** — path now known: `backend/routers/billing.py`. Add
  `15000: "autopilot"` + `25000: "professional"` to AMOUNT_TO_PLAN. Fix contradictory
  test assertions. PR #183 draft should reference correct path. S-effort ~15 min human.
  Governance critical_standing_action — not winner per rejected_paths, but actionable.

- **Item B standalone** — create `scripts/check-widget-sync.sh` + wire pre-push.
  De-couple from sprint after Item D confirms (run 48). S-effort ~15 min.

- **Item A** — scope em-dash check to skip JSX/TSX + wire Check 10 to pre-commit.
  10 min human. Still valid. Bonus B in this run's winning-concept.md.

- **email_sequences.py god-class split** — 1255L → email_crud + email_enrollment +
  email_processor. Tools ready (god-class-splitter, post-split-test-repair). M-effort ~2h.
  Do after GH #181 fix (same file area). Run 41 winner.

- **Merge safe Dependabot PRs #11-#15** — GH Actions bumps, 49 days old, safe to merge
  in batch. 5 min.

- **Merge PR #186** — eslint-parser 8.58→8.60 (minor), 8 days old. 2 min.

## Rejected This Run

- **AI-to-Human Handoff v1 as winner** — KILLED round 1: moratorium active (15 pending,
  oldest 47 days). M-effort. Same ruling as all prior moratorium runs.

- **Item A re-recommendation as winner** — KILLED: mandate switched per run 46 binding
  governance. 5 consecutive human-execute failures → mechanism must change.

## Questions for Next Run (Run 48)

1. Did nightly 2026-06-03 create `.github/workflows/lead-qualifier-eval.yml`? (check
   `ls .github/workflows/lead-qualifier-eval.yml` and `git log --oneline -5`)

2. Was GH #181 fixed by human? (grep `backend/routers/billing.py` for 15000 + 25000)

3. Was Item A done? (run `python3 scripts/check_project_invariants.py` — should exit 0
   and show Check 10 in pre-commit grep)

4. Has any sprint item (A, B, D) been completed? Count pending.

5. What is moratorium day and pending count?
