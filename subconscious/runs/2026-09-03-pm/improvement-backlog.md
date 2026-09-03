# Improvement Backlog — 2026-09-03-pm

## Active
- Step 9L: Add unapplied migration nightly alerter to `.claude/skills/nightly-commit-review/SKILL.md` — greps schema-log.md for "NOT YET APPLIED", files/updates GH issue when found. Autonomous-executable. 1st carry-forward if not done by run 116.

## Parking Lot (survived debate but not chosen)
- **M9.2 Dead Code Fix** — `engine.py` `derive_workflow_status()` inner guard always True. WEAKENED due to M9 active development (fdcbb97 today). Re-evaluate when planner_bakeoff.py and engine.py both stable for 3+ days.
- **Step 9M: Env-var / connector staleness watchdog** — Add nightly step to escalate open GH issues containing "ACCESS_TOKEN" / "expired" / "stale connector" older than 30 days. Evidence: GH #684 (42d stale). Not debated this run — promote to run 116 ideation.
- **Governance.json active_directions pruner** — archive implemented entries quarterly, keep file under 500 lines. Not debated — low urgency, no current bug. Re-evaluate at run 120.

## Rejected This Run
- **File GH issue for migrations 196/197** — KILLED. Step 9L (winner) is a strict superset: it detects unapplied migrations AND files GH issues automatically every night, making a one-shot manual filing redundant. Reason: subsumed by systemic solution.

## Questions for Next Run
1. Did nightly-2026-09-04 implement Step 9L autonomously? Check `.claude/skills/nightly-commit-review/SKILL.md` for "Step 9L" block.
2. If Step 9L is now in SKILL.md: did nightly-2026-09-04 fire it and detect migrations 196/197? Check nightly log for "Step 9L:" line.
3. Are migrations 196 and 197 still "NOT YET APPLIED" in schema-log.md? If so, was a GH issue filed?
4. M9.2 dead code: is planner_bakeoff.py stable (no commits for 3+ days)? If so, promote M9.2 fix to debate.
