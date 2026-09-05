# Improvement Backlog — 2026-09-05-pm

## Active
- **Step 9L: Nightly AI usage guard coverage sweep** — grep routers for `call_claude_messages`
  without `ai_usage_guard`, file `billing+ai-ready` GH issues for each unguarded route.
  Autonomous-executable if not approved by run 116.

## Parking Lot (survived debate but not chosen)
- **Fix Step 9G: Replace gh CLI with mcp__github__actions_run_trigger** — Step 9G is broken in
  cloud sessions (gh CLI unavailable). KB self-healing is 0% effective. Correct direction; risk:
  mcp__github__actions_run_trigger availability in nightly sessions unverified. Run 116 candidate
  once Step 9L is implemented or if MCP availability confirmed.
- **Fix Step 9J: Check all 19 Dependabot PRs per run** — Current logic skips 17/19 PRs per
  nightly (token budget). Change to check ALL for `mergeable_state: clean` (cap 5 rebase triggers
  only). Run 116 candidate if Step 9L is the winner.
- **Wire check_schema_log_drift.py into CI** — Drift guard script (43844a5) exists but is not
  enforced. Add as CI step and pre-push warning. Lower urgency (no active drift detected today).
- **os_tool_executions.py god class split** — 783 lines, 6 days stable (Rule 9 threshold met).
  Recommend module boundary proposal for human approval. Effort: M. Run 116-117 candidate.

## Rejected This Run
- None killed outright — all 5 ideas have merit. Idea 4 and Idea 2 weakened to parking lot.

## Questions for Next Run
1. Did Step 9L fire in nightly-2026-09-06? How many unguarded routes found? Issues filed?
2. Is mcp__github__actions_run_trigger available in nightly sessions (verify before fixing Step 9G)?
3. Did any of the 13 unguarded routes get a billing guard PR from issue-to-pr-loop within 24h?
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway yet? Brain connector 44d stale (GH #800).
5. os_tool_executions.py: last commit still 2026-08-30? If yes: god class split candidate for run 116.

## Run 115 Mandate for Run 116
1. Verify Step 9L present in SKILL.md (grep 'Step 9L') — should PASS if human approves winner.
2. First nightly after implementation: does nightly log contain 'Step 9L:' line? How many unguarded?
3. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? Brain connector health check (GH #800).
4. os_tool_executions.py: still stable (last commit still 2026-08-30)? If yes: god class split candidate.
5. Step 9G MCP fix: mcp__github__actions_run_trigger available in headless nightly sessions?
6. Step 9J: all 19 Dependabot PRs checked or still 17 skipped? If still skipping: run 116 winner.
