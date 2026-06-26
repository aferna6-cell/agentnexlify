# Idea 4: Track OPS Council Items as GitHub Issues

**Category:** operational
**Impact:** MEDIUM (prevents council wins from rotting in a register file)
**Effort:** XS (~5 min)
**Autonomous-executable:** YES

## Evidence
- council-fixes-register.md (2026-06-25): 7 DONE, 2 OPS items untracked
  - OPS #2: 10DLC/A2P registration needed for missed-call text-back (code ready, business action blocked)
  - OPS #9: Concierge → self-serve wizard GTM process decision needed
- Neither OPS item has a GitHub issue — no owner, no status, no reminder loop
- issue-to-pr-loop polls GH issues every 15 min; non-GH items are invisible to the loop
- Pattern from bug-patterns.md: untracked OPS items from prior audits (Twilio 10.x, pyiceberg) caused compounding confusion across sessions

## Action
Create 2 GitHub issues via mcp__github__issue_write:
1. `ops: Register 10DLC/A2P for missed-call text-back SMS (code ready, business action)` — label: ops, priority: medium
2. `ops: Define GTM process for self-serve wizard (concierge → self-serve handoff)` — label: ops, priority: low

## Expected Impact
- OPS items visible in issue-to-pr-loop + sprint planning
- Audit register no longer the only place these live
- Pattern: every council sprint OPS item → GH issue same day

## Status
**RUN 68 CANDIDATE** — autonomous, low-risk, no code change, no sequencing dependency.
