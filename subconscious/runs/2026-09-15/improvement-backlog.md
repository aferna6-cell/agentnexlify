# Improvement Backlog — Run 2026-09-15 (Run 121)

## Active

- **Step 9E credential expiry escalation: add days_remaining ≤10 threshold + GH comment filing** — extend Step 9E to fire earlier and comment on existing GH #399 for AUTOPILOT_GH_TOKEN rotation (expires 2026-10-02, 17 days). Brain PAT same. SUPABASE_ACCESS_TOKEN unknown-state GH issue. XS effort. Run 122 = autonomous-executable.

## Parking Lot (survived debate but not chosen)

- **Step 9G MCP fix: replace gh CLI with mcp__github__actions_run_trigger** — prerequisites unverified: (1) confirm kb-autopopulate.yml has `workflow_dispatch:` trigger; (2) confirm `mcp__github__actions_run_trigger` available in headless CCR nightly sessions. KB 20d stale. High impact if prerequisites verified. Run 122 candidate after verification.

- **Step 9L dedup fix: systemic-label search before duplicate GH issue** — GH #871 filed 2026-09-15 covering 20 router violations. Next nightly will try to file duplicate systemic issue because per-function dedup search won't find the systemic summary. Fix: search by `label:billing AND label:ai-ready AND "metering"` before filing. Run 122 candidate.

- **Step 9E auto-close: close credential GH issues when rotation confirmed** — when human updates credential-rotation-schedule.md and days_since_rotation resets to < 7, auto-close the open credential-rotation GH issue with success comment. Run 123 candidate.

- **os_tool_executions.py god class split** — 783L, modified 2026-09-11 (4 days ago). Stability window: need 7+ days with 0 commits before split. Re-evaluate run 123.

## Rejected This Run

- None killed in debate. Idea 2 and Idea 3 WEAKENED → parking lot.

## Questions for Next Run (Run 122)

1. Was Step 9E updated with the new threshold? If not: 3rd carry-forward = autonomous implementation.
2. Did AUTOPILOT_GH_TOKEN get rotated after GH #399 comment? Expires 2026-10-02.
3. Does kb-autopopulate.yml have `workflow_dispatch:` trigger? (verify before Step 9G fix)
4. Is `mcp__github__actions_run_trigger` available in headless CCR nightly sessions?
5. Did Step 9L file a duplicate GH issue on 2026-09-16 nightly?
