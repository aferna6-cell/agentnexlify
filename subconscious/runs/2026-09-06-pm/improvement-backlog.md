# Improvement Backlog — Run 117 (2026-09-06-pm)

## Active
- **Step 9L SKILL.md block** — Add nightly AI usage guard coverage sweep to nightly-commit-review. Detector confirmed working (30+ violations). Governance autonomous_executable fires at run 118 (3rd carry-forward). S effort, HIGH confidence.

## Parking Lot (survived debate but not chosen)

- **Step 9G cloud fix: gh CLI → mcp__github__actions_run_trigger** — KB trigger fails silently in cloud. Fix the trigger mechanism so failure becomes observable (workflow run URL in GH #403 comment). S effort. Run 118 candidate if Step 9L confirmed.

- **os_tool_executions.py god class split** — 783L, 8+ days stable, Rule 9 threshold exceeded. Split into store/executor/approval_handler. M effort. Run 118 candidate if Step 9L confirmed in SKILL.md.

- **Step 9J token-budget fix** — 17/19 Dependabot PRs skipped per token budget. Reorder Step 9J earlier in nightly session before heavier Steps 9C-9I consume budget. S effort.

## Rejected This Run

- **check_ai_metering.py CI gate** — Would fail CI on 30+ existing violations unless suppression baseline exists first. Not deployable without allowlist. Step 9L nightly approach is the correct graduated solution. Can revisit after violations are triaged.

## Questions for Next Run

1. Did Step 9L SKILL.md block get approved and implemented (check SKILL.md grep)?
2. How many of the 30+ violations were already tracked in GH? (estimate dedup rate)
3. os_tool_executions.py still stable (0 commits 10d+)? If yes and Step 9L confirmed: god class split is run 118 winner.
4. Did Step 9G trigger fix (cloud gh CLI → MCP) get actioned? KB freshness check.
5. GH #800 (SUPABASE_ACCESS_TOKEN brain connector): still open? Human actioned?
