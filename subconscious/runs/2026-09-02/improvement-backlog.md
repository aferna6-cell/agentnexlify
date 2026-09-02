# Improvement Backlog — Run 117 (2026-09-02)

## Active (Run 117 winner)
- **Step 9L/9M — ai-ready loop stall diagnostic** (workflow_efficiency, HIGH, autonomous-executable)
  - Status: recommended, awaiting human approval
  - Bonus: Step 9E 60d advisory bundled (same commit)

## Queued (next candidates)
1. **Exhaustive quote-pair test matrix for sales_exact_email.ts** (code_health, HIGH)
   - Evidence: 4 PRs in 3 days on same root cause
   - Blocker: NOT autonomous-executable; requires Cursor/human
   - Escalate to run 118 winner if ≥2 more fix PRs appear

2. **os_tool_executions.py god class split** (code_health, HIGH)
   - Evidence: 772 lines, 5 commits in 4 days
   - Blocker: file NOT stable (active sprint)
   - Re-evaluate run 118 if 0 commits in last 4 days

3. **Extract OAuth 401 refresh-once retry to shared backend utility** (code_health, MEDIUM)
   - Evidence: commit 8a60a59 gmail_connector.py; M8 Calendar OAuth incoming
   - Blocker: M8 sprint active, timing risk
   - Re-evaluate post-M8 sprint landing

4. **"Hot file" tracker in nightly** (code_health, MEDIUM)
   - Evidence: sales_exact_email pattern (3+ fix PRs on same file in 7d)
   - Deferred: lower leverage than loop stall diagnostic

## Frozen (do not propose)
- `ai_human_handoff` — rejected 3+ times, permanently frozen

## Branch context
Branch has: run 115 (2026-09-01, CRM field-omission guard), run 116 (2026-09-01-pm, Step 9L connector auth scan). This is run 117.

## Completed in this branch (per PR #713)
- Run 115 (branch): Haiku CRM field-omission guard GH issue #728 filed
- Run 116 (branch): Step 9L connector auth pattern scan — nightly SKILL.md edit
