# Improvement Backlog — Run 118 (2026-09-08)

## Active
- Create `.claude/skills/meter-ai-endpoint/SKILL.md` — 6-step skill automating the reserve/record/release billing lifecycle for AI-calling functions detected by `check_ai_metering.py`. 30+ violations live, issue-to-pr-loop stalled, 9 evidence commits this week.

## Parking Lot (survived debate but not chosen)

- **Split `os_tool_executions.py` god class** (783L, 5+ days stable) — Rule 9 violation. Revisit run 119 if Agent OS sprint adds lines. Requires gitnexus_impact analysis before execution.
- **`from __future__ import annotations` pre-commit gate for test files** — 5 test files flagged MEDIUM by nightly-2026-09-08. Easy: extend existing pre-commit hook to include `backend/tests/`. Low urgency since nightly already catches and files issues.
- **`staging-preflight` skill** — Skill discovery 2026-09-07 second proposal. Multiple features/month need staged check-only passes. Pattern exists in PR #779. Lower urgency than meter-ai-endpoint.

## Rejected This Run

- **Fix Step 9J token budget (17/19 PRs skipped)** — KILLED. Cannot write a specific action without root cause diagnosis. Root cause investigation added to run 119 mandate.

## Questions for Next Run

1. Did the human create `.claude/skills/meter-ai-endpoint/SKILL.md`? If not, assess autonomous-executable path (this is S-effort SKILL.md creation, same channel as Steps 9F/9G/9I/9J/9K).
2. How many Step 9L violations remain after nightly-2026-09-09 fires? How many GH issues filed vs dedup-skipped?
3. Step 9J token budget root cause: which step in the nightly transcript consumes the budget before Step 9J processes all 19 Dependabot PRs? (Read one nightly log.)
4. `os_tool_executions.py`: still stable (0 new commits)? If Agent OS sprint added lines, promote to run 119 winner.
5. GH #399 (AUTOPILOT_GH_TOKEN): resolved? This unblocks 30+ queued ai-ready issues including all Step 9L violation issues.
