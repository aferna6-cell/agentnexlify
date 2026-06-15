# Improvement Backlog — 2026-06-15

## Active
- **Check 13: from __future__ import annotations guard** (run 58 winner) — AUTONOMOUS-EXECUTABLE, ~10 lines bash, blocks 100%-recurrence 422 bug class. Nightly executes tonight.

## Governance Corrections This Run
- Run 55 (channels_instagram.py from __future__ + 10 em-dashes): status pending_autonomous → **IMPLEMENTED** (check_project_invariants.py PASS, violations absent from live files)
- Run 57 (widget sync cp): status pending_autonomous → **IMPLEMENTED** (check_project_invariants.py PASS — "widget assets are byte-identical across mirrors")
- Run 56 (Check 13): **remains pending_autonomous** — pre-commit ends at Check 12, confirmed by direct read

## Parking Lot (survived debate but not chosen)

| Title | ROI | Reason parked |
|-------|-----|---------------|
| Create migration 149_audit_log.sql | 1.8 | No GH issue, no customer impact, schema design needs thought |
| AI-to-Human Handoff v1 | 2.5 | MEDIUM effort, human-required, 4th recommendation — same bottleneck |
| email_sequences.py split (1143L) | 2.2 | Run 41 pending_approval; cfdd6e3 started cleanup; HUMAN-REQUIRED |
| Home.jsx split (1171L) | 1.5 | HUMAN-REQUIRED, lower urgency than code-path fixes |

## Rejected This Run
- None killed outright. Audit-log and AI-handoff WEAKENED to parking lot, not killed.

## Questions for Next Run (run 59)
1. Did nightly execute Check 13 tonight? If not, what blocked the autonomous channel?
2. Is billing.py (run 34, critical_standing_action) still missing 15000+25000? Check 11 fires WARNING on every commit — should it be escalated to FAIL?
3. With check_project_invariants.py now clean, has Check 10 (wire script into pre-commit) also been completed? Direct inspect needed.
4. Is PR #183 (billing fix) still open? 21+ days since run 51 winner.
