# Idea 1: Add `ai-ready` label to GH #385 — Activate Issue-to-PR-Loop for SMS Dashboard

**Category:** Customer Value (channel activation)  
**Effort:** XS (1 GitHub API call)  
**Autonomous:** YES — GitHub MCP `add_issue_label` or label API call  
**Moratorium impact:** ZERO — autonomous action, no human queue addition  
**Source:** Parking lot P-SMS + run 80 run_81_mandate ("verify GH issue exists and is ai-ready labeled")

---

## Evidence

GH #385 ("Add SMS Compliance Dashboard") verified OPEN as of 2026-07-07:
- Created: 2026-07-01 by nightly-commit-review
- Labels present: `nightly-review`, `backend`, `medium-risk`, `frontend`
- Labels MISSING: **`ai-ready`**

The issue-to-pr-loop polls for issues with label `ai-ready`. Without it, the loop never picks up #385. The issue has been open 6 days with the correct content (paste-ready code in `subconscious/runs/2026-06-30-pm/winning-concept.md`) but is invisible to the autonomous execution channel.

## What's Already Done

- Migration 160 applied (`sms_opt_outs` table exists)  
- Paste-ready code: backend router + React page + exact edits for 3 files (run 74)  
- GH #385 filed with full spec, acceptance criteria, invariant notes  
- Issue-to-pr-loop skill at `.claude/skills/issue-to-pr-loop/SKILL.md` — active  

## What's Missing

One label: `ai-ready`

## Impact if Executed

- Issue-to-pr-loop picks up #385 on next poll cycle (every 15 min)  
- Haiku classifies → Sonnet worktree implements (30 min)  
- PR opens automatically  
- 12/12 council score feature ships with zero human coding effort  
- Closes a TCPA liability gap that's been open 6+ weeks  

## Risk

None. Adding a label is reversible in 3 seconds. No code changed.

## Implementation

```
mcp__github__add_issue_label or mcp__github__issue_write update:
  repo: aferna6-cell/agentnexlify
  issue: 385
  add_labels: ["ai-ready"]
```

Or via: search existing labels → add `ai-ready` to #385.
