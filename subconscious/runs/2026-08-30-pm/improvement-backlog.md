# Improvement Backlog — Run 114 (2026-08-30-pm)

## Implemented This Run
- **Step 9K**: Stale subconscious draft PR audit (autonomous-executable carry-forward from run 113)
- **Step 9J detection fix**: search_pull_requests for Dependabot (bonus, same commit)

## Deferred — Watch List

### os_tool_executions.py god class split
- **Condition**: stable 3+ days (no commits)
- **Last commit**: 2026-08-30 22:04 — check again at run 117 (≈ 2026-09-02)
- **Category**: code_health
- **Risk when ready**: MEDIUM (large import surface, coordinate with M8 sprint completion)

### M8 Calendar/CRM eval → CI gate
- **Condition**: eval harness 3+ runs of stable pass_rate data
- **Created**: 2026-08-30 (eval/calendar-crm-eval-v1.json)
- **Category**: agent_performance
- **Next check**: run 117 (give harness ~1 week to accumulate data)

### SUPABASE_ACCESS_TOKEN Railway setup
- **Status**: Comment posted GH #684 (run 112, ID 5465159836) — blocked on human action
- **Category**: operational
- **Action**: none — human must set token in Railway dashboard
- **Escalation**: brain connector at 38+ days stale (threshold: 14 days)

## Frozen Ideas (do not propose)
- ai_human_handoff — rejected 3+ times, frozen per governance

## Recurring Open Loops (governance tracking)
- GH #399: AUTOPILOT_GH_TOKEN expired — issue-to-PR loop stalled
- GH #684: SUPABASE_ACCESS_TOKEN missing — brain connector stalled 38+ days
- Step 9J Dependabot detection: FIXED this run
- Step 9K subconscious PR audit: IMPLEMENTED this run
