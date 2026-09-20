# Improvement Backlog — Run 126 (2026-09-20)

## Active
- **Step 9E P0 Credential Expiry Escalation Tier** — Edit Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` to add a ≤10d days_remaining check that files a P0 GH issue with labels [human-action-required, ops, P0]. Dedup guard against existing P0 issues for same credential. AUTOPILOT_GH_TOKEN expires 2026-10-02 (12 days). P0 fires 2026-09-22 (2 days). 6th carry. Autonomous-executable mandate passed run 122.

## Parking Lot (survived debate, not chosen)

- **Step 9G SKILL.md fix** — Replace `gh workflow run` bash call in Step 9G with `mcp__github__actions_run_trigger` tool invocation. KB autopopulate has been broken for 25 days (last run 2026-08-26). MCP path confirmed available in cloud runs. One-block SKILL.md edit. Run 121 winner. 2nd carry.

- **Step 9J Dependabot major-version triage** — File consolidated GH issue tracking all 5 open major-version Dependabot PRs (#864 mcp, #863/#861 react-dom 18→19 /demo, #860 react 18→19 /frontend, #859 vitest 4→5 /frontend) with priority order (vitest first, react second, mcp third) and effort estimates. Labels: [dependencies, tech-debt, human-action-required].

- **Step 9N metering violation trend tracking** — Add Step 9N to nightly review: read previous violation count from `ops/state/ai-usage-violations.json`, compute delta, comment on GH #827 if growing, escalate if stalled 7+ runs. 45 violations unchanged (runs 123→124→125).

- **os_tool_executions.py god-class split** — Verify GH issue from run 123 is still open. If closed/missing: re-file with split plan (executor/OS-commands/validation/registry — 4 modules ~200L each). 783 lines, stable, GH issue reportedly filed run 123.

## Rejected This Run

None — all 5 ideas survived debate (2 SURVIVES, 3 WEAKENED-to-parking-lot).

## Questions for Next Run

1. Did the P0 GH issue for AUTOPILOT_GH_TOKEN fire automatically on 2026-09-22 (because someone implemented Step 9E), or is the token still unrotated and approaching expiry without a P0 issue?
2. What is the rotation status of AUTOPILOT_GH_TOKEN as of next run — has the owner responded to the urgency signals?
3. Is the Step 9G SKILL.md fix still needed, or did someone apply it in the meantime?
4. Can this run be the last carry for Step 9E? Interactive session with `/subconscious --implement` should execute the 6-carry recommendation.
