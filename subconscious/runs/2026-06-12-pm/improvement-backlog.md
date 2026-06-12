# Improvement Backlog — 2026-06-12-pm (Run 57)

## Active
- Add `from __future__` CI enforcement to pr-check.yml (AUTONOMOUS-EXECUTABLE, run 57 winner) —
  8-line YAML step, blocks violations on all commit paths regardless of hook installation.

## Pending Autonomous (carry from prior runs)
- Check 13: pre-commit `from __future__` guard in FastAPI files (run 56 winner, AUTONOMOUS-EXECUTABLE)
  — complements CI check with local-dev enforcement.
- Widget 3-Copy Sync Guard: check-widget-sync.sh + pre-push wire + CLAUDE.md fix (run 7/50 winner,
  AUTONOMOUS-EXECUTABLE, 50+ days pending).
- Wire check_project_invariants.py into pre-commit as Check 10 (run 22 winner, blocked by invariants
  exits 1 — unblocks once Bonuses A+B executed).

## Parking Lot (survived debate, not chosen)
- Fix 8 JSX em-dash violations (Bonus A, AUTONOMOUS-EXECUTABLE) — execute alongside winner.
- Remove `from __future__` from 8 backend files (Bonus B, HUMAN-REQUIRED, ~5 min) — execute alongside
  winner.
- E2E fixture tenant gap — 13 E2E journeys red after PR #254. May self-resolve tonight via
  demo_reset_job.py. Check in run 58 if still red.
- email_sequences.py god-class split (1255L, run 41 winner, pending 57+ days) — still valid; GH #181
  is critical standing action prerequisite.
- Home.jsx god-class split (1171L, run 55 finding) — HUMAN-REQUIRED.
- kb-autopopulate fix (35+ days broken, agent-browser CLI not installed) — standing operational item.
- AI-to-Human Handoff v1 (run 4 winner, 57+ days, Critical gap all 7 industries) — post-moratorium.

## Rejected This Run
- Nightly Python line deletion scope extension (Idea 5) — KILLED. CI enforcement (winner) is the
  better mechanism. Scope extension adds complexity without preventing violations at source.

## Questions for Next Run (Run 58)
1. Did nightly implement the CI YAML step (run 57 winner)? Check pr-check.yml for the new step.
2. Did nightly implement Check 13 (run 56, still pending_autonomous)?
3. Did Bonus A (em-dash) execute? Does check_project_invariants exit 0?
4. Are the 13 E2E journeys green? (demo fixture tenant auto-resolution)
5. What is the third invariant failure (not em-dash, not from __future__)?
6. Is moratorium still active? (true pending count after governance correction)
