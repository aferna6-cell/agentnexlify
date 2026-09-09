# Improvement Backlog — 2026-09-09-pm

## Active
- **os_tool_executions.py god class split** — split 783L service into 4 focused modules (<250L each): os_tool_lifecycle, os_tool_lead_actions, os_tool_email, os_tool_data_plane. Mandate winner. Human approval required.

## Parking Lot (survived debate but not chosen)

- **Fix Step 9G cloud execution path** — swap `gh workflow run` for `mcp__github__actions_run_trigger` in Step 9G. Promote when GH #403 (ANTHROPIC_API_KEY in GH Actions) is resolved; fixing trigger without key = no KB freshness improvement.
- **Step 9M: future-annotations test file cleanup** — auto-remove `from __future__ import annotations` from 5 test files (GH #823). Low risk, low urgency; CI gate (PR #834) prevents future violations. Autonomous-executable next run if mandate queue is short.
- **Step 9J token budget fix** — move Step 9J earlier in nightly SKILL.md sequence so Dependabot PR processing runs before token-heavy steps. Currently 17/19 PRs skipped due to budget exhaustion. Promote as next structural SKILL.md winner.
- **GH #800 SUPABASE_ACCESS_TOKEN CRITICAL comment** — post severity-upgraded comment reframing 44d brain connector staleness as critical customer-quality issue. Autonomous-executable bonus action (comment-only, no code).

## Rejected This Run
- None killed outright; all 5 ideas survived to parking lot or winner status.

## Questions for Next Run
1. Did Step 9L fire in nightly-2026-09-10? How many violations found? How many GH issues filed vs dedup-skipped?
2. Did the os_tool_executions.py split get approved and executed? If yes: mark implemented. If no: carry forward or escalate.
3. GH #403 (ANTHROPIC_API_KEY in GH Actions): any human action? If resolved: promote Step 9G cloud fix from parking lot.
4. Step 9J: did any of the 19 Dependabot PRs get fully processed (0 skipped) after token budget repositioning?
5. GH #823 test-file future-annotations: resolved by human or still open? If open: promote Step 9M.
